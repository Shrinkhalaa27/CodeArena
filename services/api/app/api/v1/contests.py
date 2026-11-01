from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, current_user_optional, is_staff
from app.core.errors import ApiError
from app.db import get_db
from app.models import (
    Contest,
    ContestRegistration,
    Submission,
    User,
    Verdict,
)
from app.schemas import (
    ContestDetail,
    ContestProblemOut,
    ContestSummary,
    Scoreboard,
    ScoreboardCell,
    ScoreboardRow,
)
from app.services.scoring import ScoredSubmission, compute_standings
from app.services.submissions import contest_phase

router = APIRouter(prefix="/contests", tags=["contests"])


def _summary(db: Session, c: Contest, user: User | None) -> ContestSummary:
    n = db.scalar(
        select(func.count())
        .select_from(ContestRegistration)
        .where(ContestRegistration.contest_id == c.id)
    )
    registered = bool(
        user
        and db.scalar(
            select(ContestRegistration.id).where(
                ContestRegistration.contest_id == c.id, ContestRegistration.user_id == user.id
            )
        )
    )
    return ContestSummary(
        id=c.id,
        slug=c.slug,
        title=c.title,
        description=c.description,
        start_at=c.start_at,
        end_at=c.end_at,
        freeze_at=c.freeze_at,
        phase=contest_phase(c),
        is_rated=c.is_rated,
        participants=n or 0,
        registered=registered,
    )


def _get(db: Session, slug: str) -> Contest:
    c = db.scalar(select(Contest).where(Contest.slug == slug))
    if c is None:
        raise ApiError(404, "NOT_FOUND", "Contest not found.")
    return c


@router.get("", response_model=list[ContestSummary])
def list_contests(
    db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)
):
    contests = db.scalars(
        select(Contest).where(Contest.cancelled.is_(False)).order_by(Contest.start_at.desc())
    )
    return [_summary(db, c, user) for c in contests]


@router.get("/{slug}", response_model=ContestDetail)
def get_contest(
    slug: str, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)
):
    c = _get(db, slug)
    base = _summary(db, c, user)
    started = datetime.now(UTC) >= c.start_at
    # Problem list stays hidden until the server clock says the contest has started.
    problems = (
        [
            ContestProblemOut(
                label=cp.label,
                points=cp.points,
                problem_id=cp.problem.id,
                slug=cp.problem.slug,
                title=cp.problem.title,
                difficulty=cp.problem.difficulty,
            )
            for cp in c.problems
        ]
        if started or is_staff(user)
        else []
    )
    return ContestDetail(
        **base.model_dump(),
        penalty_minutes=c.penalty_minutes,
        problems=problems,
        server_time=datetime.now(UTC),
    )


@router.post("/{slug}/register", status_code=204)
def register(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = _get(db, slug)
    if contest_phase(c) in ("ended", "cancelled"):
        raise ApiError(409, "REGISTRATION_CLOSED", "Registration is closed for this contest.")
    exists = db.scalar(
        select(ContestRegistration.id).where(
            ContestRegistration.contest_id == c.id, ContestRegistration.user_id == user.id
        )
    )
    if not exists:
        db.add(ContestRegistration(contest_id=c.id, user_id=user.id))
        db.commit()


@router.delete("/{slug}/register", status_code=204)
def unregister(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = _get(db, slug)
    if contest_phase(c) not in ("scheduled",):
        raise ApiError(
            409, "REGISTRATION_CLOSED", "You can only unregister before the contest starts."
        )
    row = db.scalar(
        select(ContestRegistration).where(
            ContestRegistration.contest_id == c.id, ContestRegistration.user_id == user.id
        )
    )
    if row:
        db.delete(row)
        db.commit()


def build_scoreboard(db: Session, c: Contest, full_view: bool) -> Scoreboard:
    phase = contest_phase(c)
    frozen = phase == "frozen" and not full_view
    registered = set(
        db.scalars(
            select(ContestRegistration.user_id).where(ContestRegistration.contest_id == c.id)
        )
    )
    subs = db.execute(
        select(
            Submission.user_id, Submission.problem_id, Submission.created_at, Submission.status
        ).where(Submission.contest_id == c.id)
    ).all()
    scored = [
        ScoredSubmission(
            user_id=u,
            problem_id=p,
            created_at=t,
            accepted=(st == Verdict.ACCEPTED.value),
            # infrastructure failures and still-pending jobs are not the participant's fault
            counts_as_attempt=st
            not in (Verdict.INTERNAL_ERROR.value, Verdict.QUEUED.value, Verdict.RUNNING.value),
        )
        for u, p, t, st in subs
        if st not in (Verdict.QUEUED.value, Verdict.RUNNING.value, Verdict.COMPILING.value)
    ]
    points = {cp.problem_id: cp.points for cp in c.problems}
    standings = compute_standings(
        scored,
        points,
        c.start_at,
        c.end_at,
        c.penalty_minutes,
        registered=registered,
        visible_until=c.freeze_at if frozen else None,
    )
    handles = {
        u.id: u.handle
        for u in db.scalars(
            select(User).where(User.id.in_([r.user_id for r in standings] or [None]))
        )
    }
    rows = []
    for r in standings:
        cells = []
        for cp in c.problems:
            cell = r.cells.get(cp.problem_id)
            cells.append(
                ScoreboardCell(
                    label=cp.label,
                    solved=bool(cell and cell.solved),
                    wrong_attempts=cell.wrong_attempts if cell else 0,
                    minutes=cell.solved_minutes if cell else None,
                )
            )
        rows.append(
            ScoreboardRow(
                rank=r.rank,
                handle=handles.get(r.user_id, "?"),
                score=r.score,
                penalty=r.penalty,
                cells=cells,
            )
        )
    return Scoreboard(contest=c.slug, phase=phase, frozen=frozen, full_view=full_view, rows=rows)


@router.get("/{slug}/scoreboard", response_model=Scoreboard)
def scoreboard(
    slug: str, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)
):
    c = _get(db, slug)
    return build_scoreboard(db, c, full_view=is_staff(user))

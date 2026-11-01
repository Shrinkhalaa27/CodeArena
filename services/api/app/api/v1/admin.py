import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.v1.contests import build_scoreboard
from app.core.errors import ApiError
from app.db import get_db
from app.models import (
    AuditLog,
    Contest,
    ContestProblem,
    Problem,
    ProblemStatus,
    RatingChange,
    Role,
    Submission,
    SubmissionResult,
    Tag,
    TestCase,
    User,
    Verdict,
)
from app.schemas import ContestIn, ProblemIn
from app.services.judge import Judge0Client
from app.services.queue import get_queue
from app.services.rating import MIN_RATED_CONTESTS_FOR_FINAL, compute_rating_changes
from app.services.submissions import contest_phase

router = APIRouter(prefix="/admin", tags=["admin"])
setter_dep = require_roles(Role.SETTER)
contest_admin_dep = require_roles(Role.CONTEST_ADMIN)
admin_dep = require_roles()  # ADMIN only


def audit(db: Session, actor: User, action: str, target: str = "", **meta) -> None:
    db.add(AuditLog(actor_id=actor.id, action=action, target=target, meta=meta))


@router.post("/problems", status_code=201)
def create_problem(
    body: ProblemIn, user: User = Depends(setter_dep), db: Session = Depends(get_db)
):
    if db.scalar(select(Problem.id).where(Problem.slug == body.slug)):
        raise ApiError(409, "SLUG_TAKEN", "A problem with that slug exists.")
    if not any(t.is_sample for t in body.test_cases):
        raise ApiError(422, "NO_SAMPLE", "At least one sample test case is required.")
    tags = []
    for name in {t.lower().strip() for t in body.tags if t.strip()}:
        tag = db.scalar(select(Tag).where(Tag.name == name)) or Tag(name=name)
        tags.append(tag)
    problem = Problem(
        **body.model_dump(exclude={"test_cases", "tags"}),
        tags=tags,
        created_by=user.id,
        status=ProblemStatus.DRAFT.value,
        test_cases=[
            TestCase(
                ordinal=i, input=t.input, expected_output=t.expected_output, is_sample=t.is_sample
            )
            for i, t in enumerate(body.test_cases, start=1)
        ],
    )
    db.add(problem)
    audit(db, user, "problem.create", body.slug)
    db.commit()
    return {"id": str(problem.id), "slug": problem.slug, "status": problem.status}


@router.get("/problems")
def list_all_problems(user: User = Depends(setter_dep), db: Session = Depends(get_db)):
    # Deliberately returns metadata only, never test data or editorial.
    return [
        {
            "id": str(p.id),
            "slug": p.slug,
            "title": p.title,
            "status": p.status,
            "difficulty": p.difficulty,
            "tests": len(p.test_cases),
        }
        for p in db.scalars(select(Problem).order_by(Problem.created_at.desc()))
    ]


@router.post("/problems/{slug}/publish")
def publish_problem(slug: str, user: User = Depends(admin_dep), db: Session = Depends(get_db)):
    p = db.scalar(select(Problem).where(Problem.slug == slug))
    if p is None:
        raise ApiError(404, "NOT_FOUND", "Problem not found.")
    if sum(1 for t in p.test_cases if not t.is_sample) < 1:
        raise ApiError(
            409, "NO_HIDDEN_TESTS", "Add at least one hidden test case before publishing."
        )
    p.status = ProblemStatus.PUBLISHED.value
    audit(db, user, "problem.publish", slug)
    db.commit()
    return {"slug": slug, "status": p.status}


@router.post("/contests", status_code=201)
def create_contest(
    body: ContestIn, user: User = Depends(contest_admin_dep), db: Session = Depends(get_db)
):
    if body.end_at <= body.start_at:
        raise ApiError(422, "BAD_WINDOW", "Contest must end after it starts.")
    if body.freeze_at and not (body.start_at < body.freeze_at <= body.end_at):
        raise ApiError(422, "BAD_FREEZE", "Freeze time must fall inside the contest window.")
    if db.scalar(select(Contest.id).where(Contest.slug == body.slug)):
        raise ApiError(409, "SLUG_TAKEN", "A contest with that slug exists.")
    contest = Contest(**body.model_dump(exclude={"problems"}))
    for cp in body.problems:
        problem = db.scalar(select(Problem).where(Problem.slug == cp.problem_slug))
        if problem is None:
            raise ApiError(422, "UNKNOWN_PROBLEM", f"Unknown problem {cp.problem_slug}.")
        contest.problems.append(
            ContestProblem(problem_id=problem.id, label=cp.label, points=cp.points)
        )
    db.add(contest)
    audit(db, user, "contest.create", body.slug)
    db.commit()
    return {"id": str(contest.id), "slug": contest.slug}


@router.post("/contests/{slug}/finalize")
def finalize_contest(
    slug: str, user: User = Depends(contest_admin_dep), db: Session = Depends(get_db)
):
    """Idempotent: ratings are written once per (user, contest); re-running changes nothing."""
    c = db.scalar(select(Contest).where(Contest.slug == slug))
    if c is None:
        raise ApiError(404, "NOT_FOUND", "Contest not found.")
    if contest_phase(c) != "ended":
        raise ApiError(409, "NOT_ENDED", "Contest has not ended.")
    if c.results_published:
        return {"status": "already_finalized"}
    if c.is_rated:
        board = build_scoreboard(db, c, full_view=True)
        users = {
            u.handle: u
            for u in db.scalars(
                select(User).where(User.handle.in_([r.handle for r in board.rows] or [""]))
            )
        }
        participants = [
            (str(users[r.handle].id), users[r.handle].rating, r.rank)
            for r in board.rows
            if r.handle in users
        ]
        new = compute_rating_changes(participants)
        for r in board.rows:
            u = users.get(r.handle)
            if u is None or db.scalar(
                select(RatingChange.id).where(
                    RatingChange.user_id == u.id, RatingChange.contest_id == c.id
                )
            ):
                continue
            u.rated_contests += 1
            db.add(
                RatingChange(
                    user_id=u.id,
                    contest_id=c.id,
                    old_rating=u.rating,
                    new_rating=new[str(u.id)],
                    rank=r.rank,
                    provisional=u.rated_contests < MIN_RATED_CONTESTS_FOR_FINAL,
                )
            )
            u.rating = new[str(u.id)]
    c.results_published = True
    audit(db, user, "contest.finalize", slug)
    db.commit()
    return {"status": "finalized"}


@router.post("/submissions/{submission_id}/rejudge", status_code=202)
def rejudge(
    submission_id: uuid.UUID, user: User = Depends(admin_dep), db: Session = Depends(get_db)
):
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise ApiError(404, "NOT_FOUND", "Submission not found.")
    previous = sub.status
    db.query(SubmissionResult).filter(SubmissionResult.submission_id == sub.id).delete()
    sub.status, sub.attempts, sub.finished_at, sub.passed_tests = Verdict.QUEUED.value, 0, None, 0
    audit(db, user, "submission.rejudge", str(sub.id), previous=previous)  # audit history preserved
    db.commit()
    get_queue().enqueue(str(sub.id))
    return {"status": "QUEUED"}


@router.get("/audit")
def audit_log(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(admin_dep),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": str(a.id),
            "actor_id": str(a.actor_id),
            "action": a.action,
            "target": a.target,
            "at": a.created_at.isoformat(),
        }
        for a in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    ]


@router.get("/judge-health")
def judge_health(user: User = Depends(contest_admin_dep)):
    from app.core.config import get_settings

    s = get_settings()
    try:
        depth = get_queue().depth()
    except Exception:  # noqa: BLE001
        depth = None
    judge_ok = True if s.judge_backend == "fake" else Judge0Client().healthy()
    return {"queue_depth": depth, "judge_backend": s.judge_backend, "judge_ok": judge_ok}

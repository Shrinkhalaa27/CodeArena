from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user_optional
from app.core.errors import ApiError
from app.db import get_db
from app.models import Problem, ProblemStatus, Submission, Tag, User, Verdict, problem_tags
from app.schemas import ProblemDetail, ProblemPage, ProblemSummary, SampleOut
from app.services.judge import STARTER_TEMPLATES, SUPPORTED_LANGUAGES

router = APIRouter(prefix="/problems", tags=["problems"])

DIFFICULTY_RANK = case(
    (Problem.difficulty == "easy", 0), (Problem.difficulty == "medium", 1), else_=2
)
SORTS = {
    "title": (Problem.title.asc(),),
    "difficulty": (DIFFICULTY_RANK.asc(), Problem.title.asc()),
    "newest": (Problem.created_at.desc(),),
}


@router.get("", response_model=ProblemPage)
def list_problems(
    q: str | None = Query(default=None, max_length=100),
    difficulty: str | None = Query(default=None, pattern="^(easy|medium|hard)$"),
    tag: str | None = Query(default=None, max_length=40),
    status: str | None = Query(default=None, pattern="^(solved|attempted|unsolved)$"),
    sort: str = Query(default="title", pattern="^(title|difficulty|newest)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(current_user_optional),
):
    stmt = select(Problem).where(Problem.status == ProblemStatus.PUBLISHED.value)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Problem.title).like(like), Problem.slug.like(like)))
    if difficulty:
        stmt = stmt.where(Problem.difficulty == difficulty)
    if tag:
        stmt = stmt.where(
            Problem.id.in_(
                select(problem_tags.c.problem_id)
                .join(Tag, Tag.id == problem_tags.c.tag_id)
                .where(Tag.name == tag.lower())
            )
        )

    user_state: dict = {}
    if user:
        rows = db.execute(
            select(
                Submission.problem_id,
                func.max(case((Submission.status == Verdict.ACCEPTED.value, 1), else_=0)),
            )
            .where(Submission.user_id == user.id, Submission.contest_id.is_(None))
            .group_by(Submission.problem_id)
        ).all()
        user_state = {pid: ("solved" if ok else "attempted") for pid, ok in rows}
        if status == "unsolved":
            stmt = stmt.where(Problem.id.not_in(list(user_state))) if user_state else stmt
        elif status:
            stmt = stmt.where(
                Problem.id.in_([pid for pid, st in user_state.items() if st == status])
            )
    elif status:
        stmt = stmt.where(Problem.id.in_([])) if status != "unsolved" else stmt

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(*SORTS[sort], Problem.id).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt))

    ids = [p.id for p in items]
    rates: dict = {}
    if ids:
        accepted = func.sum(case((Submission.status == Verdict.ACCEPTED.value, 1), else_=0))
        for pid, total_n, ok_n in db.execute(
            select(Submission.problem_id, func.count(), accepted)
            .where(Submission.problem_id.in_(ids), Submission.contest_id.is_(None))
            .group_by(Submission.problem_id)
        ):
            rates[pid] = round(100 * (ok_n or 0) / total_n, 1) if total_n else None

    return ProblemPage(
        items=[
            ProblemSummary(
                id=p.id,
                slug=p.slug,
                title=p.title,
                difficulty=p.difficulty,
                tags=sorted(t.name for t in p.tags),
                acceptance_rate=rates.get(p.id),
                status=user_state.get(p.id),
            )
            for p in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tags", response_model=list[str])
def list_tags(db: Session = Depends(get_db)):
    return [t for t in db.scalars(select(Tag.name).order_by(Tag.name))]


@router.get("/{slug}", response_model=ProblemDetail)
def get_problem(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Problem).where(Problem.slug == slug))
    if p is None or p.status != ProblemStatus.PUBLISHED.value:
        raise ApiError(404, "NOT_FOUND", "Problem not found.")
    return ProblemDetail(
        id=p.id,
        slug=p.slug,
        title=p.title,
        statement=p.statement,
        input_format=p.input_format,
        output_format=p.output_format,
        constraints=p.constraints,
        difficulty=p.difficulty,
        time_limit_ms=p.time_limit_ms,
        memory_limit_kb=p.memory_limit_kb,
        tags=sorted(t.name for t in p.tags),
        # ONLY sample cases are ever serialised. Hidden cases never leave the database layer.
        samples=[
            SampleOut(input=t.input, expected_output=t.expected_output)
            for t in p.test_cases
            if t.is_sample
        ],
        languages=list(SUPPORTED_LANGUAGES),
        templates=STARTER_TEMPLATES,
    )

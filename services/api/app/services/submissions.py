from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.models import (
    Contest,
    ContestProblem,
    ContestRegistration,
    Problem,
    ProblemStatus,
    Submission,
    User,
    Verdict,
)
from app.services.judge import SUPPORTED_LANGUAGES
from app.services.queue import JobQueue


def contest_phase(contest: Contest, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if contest.cancelled:
        return "cancelled"
    if now < contest.start_at:
        return "scheduled"
    if now > contest.end_at:
        return "ended"
    if contest.freeze_at and now >= contest.freeze_at:
        return "frozen"
    return "running"


def create_submission(
    db: Session,
    queue: JobQueue,
    user: User,
    *,
    problem_id,
    language: str,
    source_code: str,
    contest_id=None,
    idempotency_key: str | None = None,
) -> Submission:
    s = get_settings()
    if language not in SUPPORTED_LANGUAGES:
        raise ApiError(422, "UNSUPPORTED_LANGUAGE", "Language is not supported.")
    if len(source_code.encode()) > s.max_source_bytes:
        raise ApiError(422, "SOURCE_TOO_LARGE", "Source code is too large.")
    if not source_code.strip():
        raise ApiError(422, "EMPTY_SOURCE", "Source code is empty.")

    if idempotency_key:
        existing = db.scalar(
            select(Submission).where(
                Submission.user_id == user.id, Submission.idempotency_key == idempotency_key
            )
        )
        if existing:
            return existing

    problem = db.get(Problem, problem_id)
    if problem is None or problem.status != ProblemStatus.PUBLISHED.value:
        # Contest problems stay hidden before the contest starts, so check below too.
        if problem is None or not contest_id:
            raise ApiError(404, "NOT_FOUND", "Problem not found.")

    if contest_id:
        contest = db.get(Contest, contest_id)
        if contest is None:
            raise ApiError(404, "NOT_FOUND", "Contest not found.")
        in_contest = db.get(ContestProblem, (contest.id, problem.id))
        if in_contest is None:
            raise ApiError(409, "PROBLEM_NOT_IN_CONTEST", "Problem is not part of this contest.")
        now = datetime.now(UTC)  # server time is authoritative
        if contest.cancelled or not (contest.start_at <= now <= contest.end_at):
            raise ApiError(409, "CONTEST_NOT_RUNNING", "Contest is not accepting submissions.")
        reg = db.scalar(
            select(ContestRegistration).where(
                ContestRegistration.contest_id == contest.id,
                ContestRegistration.user_id == user.id,
            )
        )
        if reg is None:
            raise ApiError(403, "NOT_REGISTERED", "Register for the contest first.")
    elif problem.status != ProblemStatus.PUBLISHED.value:
        raise ApiError(404, "NOT_FOUND", "Problem not found.")

    sub = Submission(
        user_id=user.id,
        problem_id=problem.id,
        contest_id=contest_id,
        language=language,
        source_code=source_code,
        status=Verdict.QUEUED.value,
        idempotency_key=idempotency_key,
    )
    db.add(sub)
    try:
        db.commit()  # durable BEFORE we acknowledge or enqueue
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Submission).where(
                Submission.user_id == user.id, Submission.idempotency_key == idempotency_key
            )
        )
        if existing:
            return existing
        raise
    queue.enqueue(str(sub.id))
    return sub

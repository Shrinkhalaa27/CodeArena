import asyncio
import uuid

from fastapi import APIRouter, Depends, Header, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import _user_from_token, current_user
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db import SessionLocal, get_db
from app.models import FINAL_VERDICTS, Problem, ProblemStatus, Role, Submission, User
from app.schemas import (
    RunIn,
    RunOut,
    SubmissionCreated,
    SubmissionDetail,
    SubmissionIn,
    SubmissionOut,
)
from app.services.judge import SUPPORTED_LANGUAGES, JudgeInfraError, get_judge
from app.services.queue import get_queue
from app.services.ratelimit import get_limiter
from app.services.submissions import create_submission

router = APIRouter(tags=["submissions"])
FINAL = {v.value for v in FINAL_VERDICTS}


@router.post("/submissions", response_model=SubmissionCreated, status_code=202)
def submit(
    body: SubmissionIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, max_length=80),
):
    get_limiter().enforce(f"submit:{user.id}", 20, 60)
    sub = create_submission(
        db,
        get_queue(),
        user,
        problem_id=body.problem_id,
        language=body.language,
        source_code=body.source_code,
        contest_id=body.contest_id,
        idempotency_key=idempotency_key,
    )
    return SubmissionCreated(
        submission_id=sub.id,
        status=sub.status,
        created_at=sub.created_at,
        status_url=f"/api/v1/submissions/{sub.id}",
    )


@router.get("/submissions", response_model=list[SubmissionOut])
def my_submissions(
    problem_id: uuid.UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Submission).where(Submission.user_id == user.id)
    if problem_id:
        stmt = stmt.where(Submission.problem_id == problem_id)
    return list(db.scalars(stmt.order_by(Submission.created_at.desc()).limit(limit)))


@router.get("/submissions/{submission_id}", response_model=SubmissionDetail)
def get_submission(
    submission_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    sub = db.get(Submission, submission_id)
    # 404 (not 403) for other people's submissions: do not reveal that the id exists (IDOR).
    if sub is None or (sub.user_id != user.id and user.role != Role.ADMIN.value):
        raise ApiError(404, "NOT_FOUND", "Submission not found.")
    return sub


@router.post("/run", response_model=RunOut)
def run_custom(body: RunIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Run code against custom input in the isolated judge. Never executes locally."""
    s = get_settings()
    get_limiter().enforce(f"run:{user.id}", 15, 60)
    if body.language not in SUPPORTED_LANGUAGES:
        raise ApiError(422, "UNSUPPORTED_LANGUAGE", "Language is not supported.")
    if len(body.source_code.encode()) > s.max_source_bytes:
        raise ApiError(422, "SOURCE_TOO_LARGE", "Source code is too large.")
    if len(body.stdin.encode()) > s.max_custom_input_bytes:
        raise ApiError(422, "INPUT_TOO_LARGE", "Custom input is too large.")
    time_limit, mem_limit = 2000, 262144
    if body.problem_id:
        p = db.get(Problem, body.problem_id)
        if p is None or p.status != ProblemStatus.PUBLISHED.value:
            raise ApiError(404, "NOT_FOUND", "Problem not found.")
        time_limit, mem_limit = p.time_limit_ms, p.memory_limit_kb
    try:
        r = get_judge().run(
            language=body.language,
            source=body.source_code,
            stdin=body.stdin,
            time_limit_ms=time_limit,
            memory_limit_kb=mem_limit,
        )
    except JudgeInfraError:
        raise ApiError(503, "JUDGE_UNAVAILABLE", "The judge is temporarily unavailable.") from None
    status = "OK" if r.status.value == "ACCEPTED" else r.status.value
    return RunOut(
        status=status,
        stdout=r.stdout[:10000],
        compile_output=r.compile_output,
        runtime_ms=r.runtime_ms,
        memory_kb=r.memory_kb,
    )


@router.websocket("/ws/submissions/{submission_id}")
async def submission_updates(websocket: WebSocket, submission_id: uuid.UUID, token: str = ""):
    """Pushes status changes until the verdict is final. Clients may fall back to polling
    GET /submissions/{id}. (Production upgrade path: Redis pub/sub instead of DB polling.)"""
    with SessionLocal() as db:
        user = _user_from_token(db, token)
        sub = db.get(Submission, submission_id) if user else None
        if sub is None or sub.user_id != user.id:
            await websocket.close(code=4403)
            return
    await websocket.accept()
    last = None
    try:
        for _ in range(240):  # bounded: ~2 minutes
            with SessionLocal() as db:
                sub = db.get(Submission, submission_id)
                state = (sub.status, sub.passed_tests, sub.total_tests)
            if state != last:
                await websocket.send_json(
                    {"status": state[0], "passed_tests": state[1], "total_tests": state[2]}
                )
                last = state
            if state[0] in FINAL:
                break
            await asyncio.sleep(0.5)
        await websocket.close()
    except WebSocketDisconnect:
        return

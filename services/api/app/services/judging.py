"""Worker-side evaluation of one submission. Idempotent and safe to redeliver."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import FINAL_VERDICTS, Problem, Submission, SubmissionResult, TestCase, Verdict
from app.services.judge import Judge, JudgeInfraError
from app.services.normalize import outputs_match

FINAL_VALUES = {v.value for v in FINAL_VERDICTS}


def process_submission(db: Session, judge: Judge, submission_id, max_attempts: int = 3) -> str:
    """Returns 'done', 'skipped' (already final / missing) or 'retry' (transient infra failure)."""
    submission_id = uuid.UUID(str(submission_id))
    sub = db.get(Submission, submission_id)
    if sub is None or sub.status in FINAL_VALUES:
        return "skipped"  # duplicate delivery of a finished job: do nothing

    problem = db.get(Problem, sub.problem_id)
    tests = list(
        db.scalars(
            select(TestCase).where(TestCase.problem_id == sub.problem_id).order_by(TestCase.ordinal)
        )
    )
    sub.attempts += 1
    sub.status = Verdict.RUNNING.value
    sub.total_tests = len(tests)
    db.execute(delete(SubmissionResult).where(SubmissionResult.submission_id == sub.id))
    db.commit()

    results: list[SubmissionResult] = []
    final = Verdict.ACCEPTED
    compile_output = None
    max_rt, max_mem, passed = 0, 0, 0

    try:
        for tc in tests:
            run = judge.run(
                language=sub.language,
                source=sub.source_code,
                stdin=tc.input,
                time_limit_ms=problem.time_limit_ms,
                memory_limit_kb=problem.memory_limit_kb,
            )
            verdict = run.status
            if verdict == Verdict.ACCEPTED and not outputs_match(run.stdout, tc.expected_output):
                verdict = Verdict.WRONG_ANSWER
            results.append(
                SubmissionResult(
                    submission_id=sub.id,
                    test_case_id=tc.id,
                    status=verdict.value,
                    runtime_ms=run.runtime_ms,
                    memory_kb=run.memory_kb,
                )
            )
            max_rt = max(max_rt, run.runtime_ms or 0)
            max_mem = max(max_mem, run.memory_kb or 0)
            if verdict != Verdict.ACCEPTED:
                final = verdict
                if verdict == Verdict.COMPILATION_ERROR:
                    compile_output = run.compile_output
                break  # standard judging stops at the first failing case
            passed += 1
    except JudgeInfraError:
        db.rollback()
        sub = db.get(Submission, submission_id)
        if sub.attempts >= max_attempts:
            sub.status = Verdict.INTERNAL_ERROR.value
            sub.finished_at = datetime.now(UTC)
            db.commit()
            return "done"
        sub.status = Verdict.QUEUED.value
        db.commit()
        return "retry"

    # Persist per-case rows and final verdict in ONE transaction.
    db.add_all(results)
    sub.status = final.value
    sub.passed_tests = passed
    sub.runtime_ms = max_rt
    sub.memory_kb = max_mem
    sub.compile_output = compile_output
    sub.finished_at = datetime.now(UTC)
    db.commit()
    return "done"

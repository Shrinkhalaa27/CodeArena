"""Judge worker process: `python -m app.workers.judge_worker`.
Consumes submission ids from Redis, calls the isolated Judge0 service, persists verdicts."""

import logging
import signal
import time

from app.core.config import get_settings
from app.db import SessionLocal
from app.services.judge import get_judge
from app.services.judging import process_submission
from app.services.queue import JobQueue, get_queue

log = logging.getLogger("judge-worker")


def handle_one(queue: JobQueue, judge, job: str, max_attempts: int) -> str:
    with SessionLocal() as db:
        try:
            outcome = process_submission(db, judge, job, max_attempts)
        except Exception:  # noqa: BLE001
            log.exception("unexpected judging failure for %s", job)
            outcome = "retry"
    queue.ack(job)
    if outcome == "retry":
        time.sleep(1.0)
        queue.enqueue(job)
    return outcome


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    s = get_settings()
    s.validate_for_runtime()
    queue, judge = get_queue(), get_judge()
    recovered = queue.requeue_stuck()
    if recovered:
        log.info("re-queued %s jobs left by a previous worker", recovered)
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("judge worker started (backend=%s)", s.judge_backend)
    while running:
        job = queue.reserve(timeout=5)
        if job:
            outcome = handle_one(queue, judge, job, s.judge_max_attempts)
            log.info("job %s -> %s", job, outcome)


if __name__ == "__main__":
    main()

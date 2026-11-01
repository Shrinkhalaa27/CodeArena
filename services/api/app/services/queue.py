"""Submission job queue. Redis list with a processing list for crash recovery; an in-memory
implementation backs tests. Jobs carry only the submission id (never source or test data)."""

from collections import deque
from typing import Protocol

from app.core.config import get_settings

QUEUE_KEY = "codearena:judge:queue"
PROCESSING_KEY = "codearena:judge:processing"


class JobQueue(Protocol):
    def enqueue(self, submission_id: str) -> None: ...
    def reserve(self, timeout: int = 5) -> str | None: ...
    def ack(self, submission_id: str) -> None: ...
    def requeue_stuck(self) -> int: ...
    def depth(self) -> int: ...


class MemoryQueue:
    def __init__(self):
        self.items: deque[str] = deque()
        self.processing: list[str] = []

    def enqueue(self, submission_id):
        self.items.append(submission_id)

    def reserve(self, timeout=5):
        if not self.items:
            return None
        job = self.items.popleft()
        self.processing.append(job)
        return job

    def ack(self, submission_id):
        if submission_id in self.processing:
            self.processing.remove(submission_id)

    def requeue_stuck(self):
        n = len(self.processing)
        self.items.extend(self.processing)
        self.processing.clear()
        return n

    def depth(self):
        return len(self.items)


class InlineQueue:
    """Development/E2E only (QUEUE_BACKEND=inline, refused in production): judges in a background
    thread of the API process so the stack runs without Redis. Execution is still delegated to the
    judge adapter; the API process never runs submitted code itself."""

    def enqueue(self, submission_id):
        import threading

        threading.Thread(target=self._work, args=(submission_id,), daemon=True).start()

    def _work(self, submission_id):
        from app.db import SessionLocal
        from app.services.judge import get_judge
        from app.services.judging import process_submission

        s = get_settings()
        for _ in range(s.judge_max_attempts):
            with SessionLocal() as db:
                if (
                    process_submission(db, get_judge(), submission_id, s.judge_max_attempts)
                    != "retry"
                ):
                    return

    def reserve(self, timeout=5):
        return None

    def ack(self, submission_id):
        pass

    def requeue_stuck(self):
        return 0

    def depth(self):
        return 0


class RedisQueue:
    def __init__(self, url: str):
        import redis

        self.r = redis.Redis.from_url(url, decode_responses=True)

    def enqueue(self, submission_id):
        self.r.lpush(QUEUE_KEY, submission_id)

    def reserve(self, timeout=5):
        return self.r.brpoplpush(QUEUE_KEY, PROCESSING_KEY, timeout=timeout)

    def ack(self, submission_id):
        self.r.lrem(PROCESSING_KEY, 1, submission_id)

    def requeue_stuck(self):
        """Call on worker start: anything left in 'processing' died with a previous worker.
        Processing is idempotent, so redelivery is safe."""
        n = 0
        while self.r.rpoplpush(PROCESSING_KEY, QUEUE_KEY):
            n += 1
        return n

    def depth(self):
        return int(self.r.llen(QUEUE_KEY))


_queue: JobQueue | None = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        s = get_settings()
        if s.queue_backend == "memory":
            _queue = MemoryQueue()
        elif s.queue_backend == "inline":
            _queue = InlineQueue()
        else:
            _queue = RedisQueue(s.redis_url)
    return _queue


def set_queue(q: JobQueue | None) -> None:
    global _queue
    _queue = q

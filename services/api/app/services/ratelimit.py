"""Fixed-window rate limiter. Redis-backed when available, in-memory otherwise (single process)."""

import time
from collections import defaultdict

from app.core.config import get_settings
from app.core.errors import ApiError


class RateLimiter:
    def __init__(self):
        self._mem: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._redis = None
        s = get_settings()
        if s.queue_backend == "redis" and s.redis_url:
            try:
                import redis

                self._redis = redis.Redis.from_url(s.redis_url, socket_timeout=0.5)
            except Exception:  # noqa: BLE001
                self._redis = None

    def hit(self, key: str, limit: int, window_s: int) -> bool:
        if self._redis is not None:
            try:
                k = f"rl:{key}:{int(time.time() // window_s)}"
                n = self._redis.incr(k)
                if n == 1:
                    self._redis.expire(k, window_s)
                return n <= limit
            except Exception:  # noqa: BLE001  fall back to memory if Redis is down
                pass
        now = time.monotonic()
        count, reset = self._mem[key]
        if now >= reset:
            count, reset = 0, now + window_s
        count += 1
        self._mem[key] = (count, reset)
        return count <= limit

    def enforce(self, key: str, limit: int, window_s: int) -> None:
        if not self.hit(key, limit, window_s):
            raise ApiError(429, "RATE_LIMITED", "Too many requests. Please slow down.")


_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def reset_limiter() -> None:
    global _limiter
    _limiter = None

from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import time

from fastapi import HTTPException, Request, status

from app.core.config import settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time()
        window_start = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry_after
            bucket.append(now)
            return True, 0

    def count(self, key: str, window_seconds: int) -> int:
        now = time()
        window_start = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            return len(bucket)

    def add_event(self, key: str) -> None:
        with self._lock:
            self._events[key].append(time())

    def retry_after(self, key: str, window_seconds: int) -> int:
        now = time()
        window_start = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            if not bucket:
                return 0
            return max(1, int(window_seconds - (now - bucket[0])))

    def clear_key(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def limit_by_ip(scope: str, limit: int, window_seconds: int) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        ip = get_client_ip(request)
        key = f"{scope}:{ip}"
        allowed, retry_after = rate_limiter.check(key, limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {scope}. Retry after {retry_after} seconds",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency

"""
Rate limiting middleware.

A simple fixed-window limiter keyed by client IP, implemented in-process
with no external dependency (no Redis, no third-party service). This is
an intentional trade-off documented in the README: a single-process,
in-memory limiter is appropriate for this deployment's scale, and the
same interface (`is_allowed`) is what a Redis-backed implementation would
expose if this were ever scaled across multiple processes.
"""

import time
from collections import deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimiter:
    """Fixed-window request counter per client key."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = {}
        self.last_cleanup = time.monotonic()

    def is_allowed(self, key: str, now: float | None = None) -> bool:
        current_time = time.monotonic() if now is None else now
        window_start = current_time - self.window_seconds

        # Periodically clean up all expired keys to prevent memory leak.
        # Run cleanup at most once per window.
        if (current_time - self.last_cleanup) > self.window_seconds:
            self.cleanup(current_time)

        # Retrieve or initialize deque for this key
        if key not in self._hits:
            self._hits[key] = deque()
        hits = self._hits[key]

        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return False

        hits.append(current_time)
        return True

    def cleanup(self, now: float) -> None:
        """Prunes expired hits for all keys, and removes keys that have no active hits."""
        window_start = now - self.window_seconds
        expired_keys = []

        for key, hits in self._hits.items():
            while hits and hits[0] < window_start:
                hits.popleft()
            if not hits:
                expired_keys.append(key)

        for key in expired_keys:
            del self._hits[key]

        self.last_cleanup = now


# 30 requests per 60 seconds per client is generous for a single fan
# interacting with the concierge, while still bounding worst-case load
# from a single misbehaving client.
chat_rate_limiter = RateLimiter(max_requests=30, window_seconds=60)

RATE_LIMITED_PATHS = {"/api/chat"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies `chat_rate_limiter` to the paths in `RATE_LIMITED_PATHS`."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in RATE_LIMITED_PATHS:
            x_forwarded_for = request.headers.get("x-forwarded-for")
            if x_forwarded_for:
                client_key = x_forwarded_for.split(",")[0].strip()
            else:
                client_key = request.client.host if request.client else "unknown"

            if not chat_rate_limiter.is_allowed(client_key):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down and try again shortly."},
                )
        return await call_next(request)

"""
Simple in-process sliding-window rate limiter used as a route dependency.
Per worker only — move to Redis when running multiple instances.
"""

import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.exceptions import RateLimitedError

_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(bucket: str, per_minute: int):
    async def dependency(request: Request) -> None:
        limit = per_minute
        settings = getattr(request.app.state, "settings", None)
        if settings is not None and bucket == "auth":
            limit = settings.rate_limit_auth_per_minute
        client = request.client.host if request.client else "unknown"
        key = f"{bucket}:{client}"
        now = time.monotonic()
        window = _hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            raise RateLimitedError("Too many requests, slow down", details={"retry_after_seconds": int(60 - (now - window[0])) + 1})
        window.append(now)

    return dependency


def reset_rate_limits() -> None:
    _hits.clear()

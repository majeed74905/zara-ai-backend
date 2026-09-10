"""
Production Rate Limiter for Zara AI
────────────────────────────────────
Thread-safe, in-memory sliding-window rate limiter.
Protects AI provider quotas and auth endpoints against request flooding.
"""

import time
import threading
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
import logging

logger = logging.getLogger(__name__)

class SlidingWindowLimiter:
    def __init__(self):
        # key -> list of float timestamps
        self._records: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    def _cleanup(self, now: float, max_window: int = 120):
        """Purge entries older than max_window seconds."""
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        expired_keys = []
        for key, timestamps in self._records.items():
            valid = [ts for ts in timestamps if now - ts < max_window]
            if not valid:
                expired_keys.append(key)
            else:
                self._records[key] = valid
        for k in expired_keys:
            del self._records[k]

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        Returns: (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        with self._lock:
            self._cleanup(now, window_seconds * 2)
            timestamps = self._records.get(key, [])
            cutoff = now - window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            if len(valid_timestamps) >= max_requests:
                earliest = valid_timestamps[0]
                retry_after = max(1, int(window_seconds - (now - earliest)))
                return False, retry_after

            valid_timestamps.append(now)
            self._records[key] = valid_timestamps
            return True, 0

limiter = SlidingWindowLimiter()

def get_client_ip(request: Request) -> str:
    """Extract client IP handling proxies safely."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in X-Forwarded-For is client
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

def rate_limit_check(scope: str = "chat", max_requests: int = 30, window_seconds: int = 60):
    """
    FastAPI dependency for endpoint-level rate limiting.
    Default for chat: 30 requests per minute per IP.
    """
    async def dependency(request: Request):
        client_ip = get_client_ip(request)
        key = f"{scope}:{client_ip}"
        allowed, retry_after = limiter.is_allowed(key, max_requests, window_seconds)
        if not allowed:
            logger.warning(f"Rate limit exceeded for {key}. Retry after {retry_after}s.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again in a moment.",
                headers={"Retry-After": str(retry_after)}
            )
    return dependency

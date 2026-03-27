"""
In-Memory Response Cache for Zara AI — Phase 3
───────────────────────────────────────────────
Simple TTL-based LRU cache for LLM responses.

Design choices:
  - In-memory only (no Redis dependency for local/small deployments).
  - MD5 hash of (mode + language + message) as cache key.
  - TTL configurable per entry (default 5 minutes).
  - Thread-safe with a simple lock.
  - Max 500 entries to prevent unbounded growth.
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_MAX_SIZE = 500
_CACHE_DEFAULT_TTL = 300  # seconds (5 min)

_cache: OrderedDict = OrderedDict()
_lock = threading.Lock()


def _make_key(mode: str, language: str, message: str, module: str) -> str:
    raw = f"{mode}|{language}|{module}|{message.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_cached(mode: str, language: str, message: str, module: str) -> Optional[str]:
    """Return cached response if it exists and hasn't expired."""
    key = _make_key(mode, language, message, module)
    with _lock:
        if key in _cache:
            value, expiry = _cache[key]
            if time.time() < expiry:
                _cache.move_to_end(key)  # LRU touch
                logger.info(f"Cache HIT for key={key[:8]}...")
                return value
            else:
                del _cache[key]
                logger.debug(f"Cache EXPIRED for key={key[:8]}...")
    return None


def set_cached(
    mode: str,
    language: str,
    message: str,
    module: str,
    response: str,
    ttl: int = _CACHE_DEFAULT_TTL,
) -> None:
    """Store a response in cache with TTL."""
    key = _make_key(mode, language, message, module)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
        _cache[key] = (response, time.time() + ttl)
        if len(_cache) > _CACHE_MAX_SIZE:
            evicted_key, _ = _cache.popitem(last=False)
            logger.debug(f"Cache EVICT oldest key={evicted_key[:8]}...")
    logger.info(f"Cache SET key={key[:8]}... TTL={ttl}s")


def cache_stats() -> dict:
    """Return basic cache statistics."""
    with _lock:
        now = time.time()
        valid = sum(1 for _, (_, exp) in _cache.items() if exp > now)
        return {
            "total_entries": len(_cache),
            "valid_entries": valid,
            "expired_entries": len(_cache) - valid,
            "max_size": _CACHE_MAX_SIZE,
        }


def clear_cache() -> None:
    """Clear all cached entries."""
    with _lock:
        _cache.clear()
    logger.info("Cache CLEARED")

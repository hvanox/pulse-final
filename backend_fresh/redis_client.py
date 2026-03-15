"""
Redis client — caching, rate-limiting, session storage.

Falls back to an in-memory dict when Redis is unavailable (dev / tests).
"""

import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")

# ── lazy import so the app starts without redis installed ────────────────────
try:
    import redis.asyncio as aioredis  # redis>=4.2
    _redis_available = True
except ImportError:
    _redis_available = False
    logger.warning("redis package not installed — using in-memory fallback")


class FallbackCache:
    """Tiny in-memory cache used when Redis is not available."""

    def __init__(self):
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int = 300) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def incr(self, key: str) -> int:
        self._store[key] = int(self._store.get(key, 0)) + 1
        return self._store[key]

    async def expire(self, key: str, seconds: int) -> None:
        pass  # no TTL in the simple fallback

    async def close(self) -> None:
        pass


_client: Optional[Any] = None


async def get_redis():
    global _client
    if _client is not None:
        return _client

    if _redis_available and REDIS_URL:
        try:
            _client = aioredis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _client.ping()
            logger.info("Connected to Redis at %s", REDIS_URL)
            return _client
        except Exception as exc:
            logger.warning("Redis connection failed (%s) — using in-memory cache", exc)

    _client = FallbackCache()
    return _client


# ── helpers ──────────────────────────────────────────────────────────────────

async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    r = await get_redis()
    await r.set(key, json.dumps(value), ex=ttl)


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def cache_invalidate_prefix(prefix: str) -> None:
    """Delete all keys matching prefix:* (only works with real Redis)."""
    r = await get_redis()
    if isinstance(r, FallbackCache):
        keys = [k for k in r._store if k.startswith(prefix)]
        for k in keys:
            del r._store[k]
        return
    async for key in r.scan_iter(f"{prefix}:*"):
        await r.delete(key)


# ── rate limiter ─────────────────────────────────────────────────────────────

async def is_rate_limited(identifier: str, limit: int = 60, window: int = 60) -> bool:
    """
    Sliding-window rate limiter.
    Returns True if the identifier has exceeded `limit` requests in `window` seconds.
    """
    r = await get_redis()
    key = f"rl:{identifier}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window)
    return int(count) > limit


# ── decorator ────────────────────────────────────────────────────────────────

def cached(prefix: str, ttl: int = 300, key_fn: Optional[Callable] = None):
    """
    Async function decorator that caches the return value in Redis.

    Usage:
        @cached("stocks", ttl=60)
        async def get_stocks(user_id: int): ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key_parts = key_fn(*args, **kwargs) if key_fn else f"{args}:{kwargs}"
            cache_key = f"{prefix}:{cache_key_parts}"
            cached_value = await cache_get(cache_key)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            await cache_set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator

"""
CodeSentinel Backend: Redis Connection & Client Management.

Provides asynchronous Redis connection pooling and health checks.
"""

from typing import Optional
import redis.asyncio as aioredis
from .config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Obtain or initialize the global asynchronous Redis client pool."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the global Redis client connection pool."""
    global _redis_client
    if _redis_client is not None:
        if hasattr(_redis_client, "aclose"):
            await _redis_client.aclose()
        else:
            await _redis_client.close()
        _redis_client = None

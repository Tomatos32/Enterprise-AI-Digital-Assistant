"""Redis Connection Manager and Pool Factory."""

import redis.asyncio as aioredis
from backend.core.config import settings

# Global Redis Connection Pool
redis_pool = None


async def get_redis_client() -> aioredis.Redis:
    """
    Returns an async Redis client instance from connection pool.
    """
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    return aioredis.Redis(connection_pool=redis_pool)


async def check_redis_health() -> bool:
    """
    Checks Redis connectivity.
    """
    try:
        client = await get_redis_client()
        return await client.ping()
    except Exception:
        return False

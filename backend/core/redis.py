"""Redis Connection Manager supporting Standalone & Sentinel High Availability."""

import logging
from typing import Optional, List, Tuple
import redis.asyncio as aioredis
from redis.asyncio.sentinel import Sentinel
from backend.core.config import settings

logger = logging.getLogger("redis_manager")

# Global Redis Connection Pool / Client
redis_pool: Optional[aioredis.ConnectionPool] = None
redis_client: Optional[aioredis.Redis] = None


def parse_sentinel_hosts(sentinel_hosts_str: str) -> List[Tuple[str, int]]:
    """Parses comma-separated host:port string into a list of tuples."""
    hosts = []
    for item in sentinel_hosts_str.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            host, port = item.split(":", 1)
            hosts.append((host.strip(), int(port.strip())))
        else:
            hosts.append((item, 26379))
    return hosts


async def get_redis_client() -> aioredis.Redis:
    """
    Returns an async Redis client instance.
    Supports:
    1. Sentinel Mode if REDIS_USE_SENTINEL=True
    2. Standalone Pooled Redis instance as default fallback
    """
    global redis_pool, redis_client

    use_sentinel = getattr(settings, "REDIS_USE_SENTINEL", False)
    sentinel_hosts_str = getattr(settings, "REDIS_SENTINEL_HOSTS", "")
    sentinel_master_name = getattr(settings, "REDIS_SENTINEL_MASTER_NAME", "mymaster")

    if use_sentinel and sentinel_hosts_str:
        try:
            sentinels = parse_sentinel_hosts(sentinel_hosts_str)
            sentinel = Sentinel(
                sentinels,
                socket_timeout=getattr(settings, "REDIS_SENTINEL_TIMEOUT", 2.0),
                decode_responses=True
            )
            # Master connection with auto failover
            return sentinel.master_for(
                sentinel_master_name,
                db=settings.REDIS_DB,
                decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Redis Sentinel connection failed, falling back to standalone: {e}")

    # Standalone Redis Pool
    if redis_pool is None:
        redis_pool = aioredis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            max_connections=getattr(settings, "REDIS_MAX_CONNECTIONS", 100),
            decode_responses=True
        )
    return aioredis.Redis(connection_pool=redis_pool)


async def check_redis_health() -> bool:
    """Checks Redis connectivity (works with both Sentinel and Standalone)."""
    try:
        client = await get_redis_client()
        return await client.ping()
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return False

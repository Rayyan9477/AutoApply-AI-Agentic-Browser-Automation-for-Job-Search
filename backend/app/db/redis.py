"""Async Redis connection pool management."""

import structlog
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)

_redis_pool: ConnectionPool | None = None
_redis_client: Redis | None = None


async def init_redis_pool(redis_url: str) -> None:
    """Initialize the global Redis connection pool.

    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379/0).
    """
    global _redis_pool, _redis_client

    try:
        _redis_pool = ConnectionPool.from_url(
            redis_url,
            max_connections=20,
            decode_responses=True,
        )
        _redis_client = Redis(connection_pool=_redis_pool)
        # Verify connectivity
        await _redis_client.ping()
        logger.info("redis_connected", url=redis_url)
    except RedisError as e:
        logger.warning(
            "redis_connection_failed",
            url=redis_url,
            error=str(e),
        )
        _redis_pool = None
        _redis_client = None


async def close_redis_pool() -> None:
    """Close the Redis connection pool gracefully."""
    global _redis_pool, _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("redis_disconnected")


def get_redis() -> Redis | None:
    """Get the Redis client instance.

    Returns None if Redis is not available (graceful degradation).
    """
    return _redis_client


async def is_redis_available() -> bool:
    """Check if Redis connection is alive."""
    if _redis_client is None:
        return False
    try:
        await _redis_client.ping()
        return True
    except RedisError:
        return False

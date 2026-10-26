import uuid
from typing import Optional

import structlog
from arq.connections import ArqRedis, RedisSettings, create_pool

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Global cached ARQ Redis pool instance
_arq_redis_pool: Optional[ArqRedis] = None


def get_redis_settings() -> RedisSettings:
    """Parses application REDIS_URL into an ARQ RedisSettings instance."""
    return RedisSettings.from_dsn(settings.REDIS_URL)


async def get_arq_redis_pool() -> Optional[ArqRedis]:
    """Retrieves or initializes the global ARQ Redis connection pool.

    Returns None gracefully if the Redis host is unreachable or connection fails.
    """
    global _arq_redis_pool
    if _arq_redis_pool is not None:
        return _arq_redis_pool

    try:
        redis_settings = get_redis_settings()
        _arq_redis_pool = await create_pool(redis_settings)
        logger.info(
            "arq_redis_pool_initialized",
            host=redis_settings.host,
            port=redis_settings.port,
        )
        return _arq_redis_pool
    except Exception as exc:
        logger.warning(
            "arq_redis_pool_connection_failed",
            error=str(exc),
            redis_url=settings.REDIS_URL,
        )
        return None


async def close_arq_redis_pool() -> None:
    """Closes the ARQ Redis connection pool if initialized."""
    global _arq_redis_pool
    if _arq_redis_pool is not None:
        try:
            await _arq_redis_pool.close()
            logger.info("arq_redis_pool_closed")
        except Exception as exc:
            logger.warning("arq_redis_pool_close_failed", error=str(exc))
        finally:
            _arq_redis_pool = None


async def enqueue_clone_job(project_id: uuid.UUID | str) -> Optional[str]:
    """Enqueues a clone_and_sanitize_repository background task in ARQ.

    Gracefully logs and returns None if Redis is offline or unavailable.
    """
    pool = await get_arq_redis_pool()
    if pool is None:
        logger.warning(
            "clone_job_skipped_redis_offline",
            project_id=str(project_id),
        )
        return None

    try:
        job = await pool.enqueue_job("clone_and_sanitize_repository", str(project_id))
        job_id = job.job_id if job else None
        logger.info(
            "clone_job_enqueued",
            project_id=str(project_id),
            job_id=job_id,
        )
        return job_id
    except Exception as exc:
        logger.error(
            "clone_job_enqueue_failed",
            project_id=str(project_id),
            error=str(exc),
        )
        return None

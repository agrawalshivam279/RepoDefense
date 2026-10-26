from typing import Any

import structlog

from app.core.redis import get_redis_settings
from app.workers.cloner import clone_and_sanitize_repository

logger = structlog.get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Invoked when the ARQ worker process starts up."""
    logger.info("arq_worker_starting_up")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Invoked when the ARQ worker process shuts down."""
    logger.info("arq_worker_shutting_down")


class WorkerSettings:
    """ARQ Worker configuration settings."""

    functions = [clone_and_sanitize_repository]
    redis_settings = get_redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300
    keep_result = 3600

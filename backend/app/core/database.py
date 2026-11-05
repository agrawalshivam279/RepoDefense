import os
import sys
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# In test environments (pytest or TESTING=true), use NullPool to prevent asyncpg
# connections from being pooled and reused across separate anyio event loops.
_is_testing = "pytest" in sys.modules or os.getenv("TESTING") == "true"

if _is_testing:
    engine = create_async_engine(
        url=settings.DATABASE_URL,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        url=settings.DATABASE_URL,
        pool_size=10,
        max_overflow=5,
        pool_recycle=300,
        pool_pre_ping=True,
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an isolated async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

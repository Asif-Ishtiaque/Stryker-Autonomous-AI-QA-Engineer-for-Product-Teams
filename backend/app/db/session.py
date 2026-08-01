from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=20, max_overflow=10)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def dispose_stale_pool() -> None:
    """Drops any pooled asyncpg connections left over from a previous asyncio event loop.

    `engine` is a module-level singleton, imported once per process — fine for FastAPI,
    which runs one event loop for the process's whole lifetime. It's NOT fine for Celery:
    each task invocation calls `asyncio.run(...)`, which tears the loop down when the task
    finishes. A connection checked back into the pool during task N is bound to that now-
    closed loop; task N+1 (same worker process, fresh loop) reusing it fails with
    `RuntimeError: ... attached to a different loop` or `Event loop is closed` — this was
    observed crashing a real run outright. Call this once at the start of every Celery task
    entrypoint, before any session use, so the pool is empty and every connection it opens
    belongs to the loop that's about to use it.
    """
    await engine.dispose()


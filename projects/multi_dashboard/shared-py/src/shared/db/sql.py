"""Async SQLAlchemy 2.x engine + session factory.

Backends construct one engine per process via :func:`make_async_engine`,
build a session factory once, and depend on :func:`get_async_session` in
their routes::

    from shared.db.sql import make_async_engine, make_async_session_factory

    engine = make_async_engine(settings.scheduler_database_url)
    SessionLocal = make_async_session_factory(engine)

    async def get_db() -> AsyncIterator[AsyncSession]:
        async with SessionLocal() as session:
            yield session

ACID note: every request gets its own ``AsyncSession``; commits happen at the
end of CRUD functions or via the dependency's ``__aexit__``.
"""
from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_async_engine(
    url: str,
    *,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
) -> AsyncEngine:
    """Create an async engine. URL must use an async driver (``+asyncpg`` /
    ``+aiosqlite``)."""
    # aiosqlite doesn't accept pool size kwargs the same way; gate them.
    is_sqlite = url.startswith("sqlite")
    kwargs: dict = {"echo": echo, "pool_pre_ping": pool_pre_ping}
    if not is_sqlite:
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = max_overflow
    return create_async_engine(url, **kwargs)


def make_async_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Build a session factory bound to ``engine``."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Async-generator session scope for use as a FastAPI dep::

        async def get_db():
            async for s in session_scope(SessionLocal):
                yield s
    """
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "AsyncEngine",
    "AsyncSession",
    "async_sessionmaker",
    "make_async_engine",
    "make_async_session_factory",
    "session_scope",
]

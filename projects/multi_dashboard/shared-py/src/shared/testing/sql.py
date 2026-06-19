"""In-memory async SQLite fixtures for SQL service tests.

Services pass their declarative ``Base`` to ``init_models`` so tables are
created per-test::

    @pytest.fixture
    async def db_session(sqlite_engine):
        from app.models import Base
        await init_models(sqlite_engine, Base)
        async with async_sessionmaker(sqlite_engine, expire_on_commit=False)() as s:
            yield s
"""
from __future__ import annotations

from typing import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


@pytest.fixture
async def sqlite_engine() -> AsyncIterator[AsyncEngine]:
    """A throwaway aiosqlite engine — one per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        yield engine
    finally:
        await engine.dispose()


async def init_models(engine: AsyncEngine, base) -> None:
    """Create all tables defined on ``base.metadata``."""
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)


__all__ = ["init_models", "sqlite_engine"]

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from . import lifespan as _lifespan_mod


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession per request."""
    factory = _lifespan_mod.get_session_factory()
    async with factory() as session:
        yield session


def get_redis() -> Any:
    return _lifespan_mod.get_redis()


__all__ = ["get_db", "get_redis"]

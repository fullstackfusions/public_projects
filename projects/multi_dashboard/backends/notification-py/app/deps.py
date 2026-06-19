"""FastAPI dependency providers for notification-backend."""
from __future__ import annotations

from collections.abc import AsyncIterator

import redis.asyncio as aioredis
from shared.auth import get_current_user_factory
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .lifespan import get_redis_client, get_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a per-request AsyncSession, rolling back on exception."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    """Return the shared Redis client (no yield — client is long-lived)."""
    return get_redis_client()


# Pre-built dependency — raises 401 envelope when token is absent or invalid.
get_current_user = get_current_user_factory(
    secret_provider=lambda: get_settings().auth_secret_key,
    algorithm="HS256",
)

__all__ = ["get_db", "get_redis", "get_current_user"]

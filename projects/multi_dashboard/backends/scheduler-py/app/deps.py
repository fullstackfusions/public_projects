"""FastAPI dependency providers for scheduler-backend.

Centralises all dependency factories so routers never call raw constructors.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from shared.auth import get_current_user_factory
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .lifespan import get_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a per-request AsyncSession, rolling back on exception."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Pre-built dependency: raises AuthError (→ 401 envelope) when token is absent
# or invalid. Falls back to ?access_token= query param for WS/SSE clients.
get_current_user = get_current_user_factory(
    secret_provider=lambda: get_settings().auth_secret_key,
    algorithm="HS256",
)


__all__ = ["get_db", "get_current_user"]

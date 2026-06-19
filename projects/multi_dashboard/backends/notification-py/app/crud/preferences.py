"""Async data-access functions for UserPreference."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.preference import UserPreference


async def get_preference(db: AsyncSession, user_id: str) -> UserPreference | None:
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    return result.scalar_one_or_none()


async def get_or_create_preference(db: AsyncSession, user_id: str) -> UserPreference:
    """Return existing preference row or create a blank one (no channels enabled)."""
    pref = await get_preference(db, user_id)
    if pref is None:
        pref = UserPreference(user_id=user_id, enabled_channels=[])
        db.add(pref)
        await db.flush()
        await db.refresh(pref)
    return pref


async def upsert_preference(
    db: AsyncSession,
    user_id: str,
    updates: dict[str, object],
) -> UserPreference:
    """Update fields on an existing preference row, creating it if absent."""
    pref = await get_or_create_preference(db, user_id)
    for key, value in updates.items():
        setattr(pref, key, value)
    pref.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(pref)
    return pref


__all__ = ["get_preference", "get_or_create_preference", "upsert_preference"]

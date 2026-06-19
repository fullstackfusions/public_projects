"""User notification preferences endpoints.

GET /preferences/me  — return current preferences for the authenticated user
PUT /preferences/me  — upsert preferences (creates row on first call)

The user_id is always taken from the JWT sub claim — clients cannot
impersonate another user.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from shared.auth import TokenClaims
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import preferences as pref_crud
from ..deps import get_current_user, get_db
from ..schemas.notification import UserPreferenceOut, UserPreferenceUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/me", response_model=UserPreferenceOut)
async def get_my_preferences(
    db: AsyncSession = Depends(get_db),
    user: TokenClaims = Depends(get_current_user),
) -> UserPreferenceOut:
    """Return (or create) the preference row for the authenticated user."""
    pref = await pref_crud.get_or_create_preference(db, user.sub)
    await db.commit()
    return UserPreferenceOut.model_validate(pref)


@router.put("/me", response_model=UserPreferenceOut)
async def update_my_preferences(
    payload: UserPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenClaims = Depends(get_current_user),
) -> UserPreferenceOut:
    """Upsert notification preferences for the authenticated user."""
    updates = payload.model_dump(exclude_unset=True)
    pref = await pref_crud.upsert_preference(db, user.sub, updates)
    await db.commit()
    return UserPreferenceOut.model_validate(pref)


__all__ = ["router"]

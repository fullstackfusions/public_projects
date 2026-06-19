from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..security import hash_password


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str | None = None,
    name: str | None = None,
    picture_url: str | None = None,
    google_sub: str | None = None,
    role: str = "user",
) -> User:
    user = User(
        email=email,
        name=name,
        picture_url=picture_url,
        google_sub=google_sub,
        password_hash=hash_password(password) if password else None,
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, updates: dict[str, Any]) -> User:
    for k, v in updates.items():
        setattr(user, k, v)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def upsert_google_user(
    db: AsyncSession,
    *,
    google_sub: str,
    email: str,
    name: str | None,
    picture_url: str | None,
) -> User:
    """Link Google identity to existing user or create new user."""
    user = await get_user_by_google_sub(db, google_sub)
    if user:
        return await update_user(db, user, {"name": name, "picture_url": picture_url})

    user = await get_user_by_email(db, email)
    if user:
        return await update_user(
            db, user, {"google_sub": google_sub, "name": name, "picture_url": picture_url}
        )

    return await create_user(
        db,
        email=email,
        google_sub=google_sub,
        name=name,
        picture_url=picture_url,
    )

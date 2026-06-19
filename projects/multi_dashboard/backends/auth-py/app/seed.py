"""Idempotent user seeding from SEED_USERS env var."""
from __future__ import annotations

from shared.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

from .crud.users import create_user, get_user_by_email

logger = get_logger(__name__)


async def seed_users(db: AsyncSession, seed_users_str: str) -> None:
    """Upsert seed users defined in SEED_USERS env var.

    Format: ``username:password:role:email,username2:...``
    The 'username' field is used as the display name.
    """
    if not seed_users_str.strip():
        return

    for entry in seed_users_str.split(","):
        parts = entry.strip().split(":")
        if len(parts) < 4:
            logger.warning("Skipping malformed seed entry", extra={"entry": entry})
            continue

        username, password, role, email = parts[0], parts[1], parts[2], parts[3]

        existing = await get_user_by_email(db, email)
        if existing:
            logger.debug("Seed user already exists", extra={"email": email})
            continue

        await create_user(
            db,
            email=email,
            password=password,
            name=username.title(),
            role=role,
        )
        logger.info("Seeded user", extra={"email": email, "role": role})

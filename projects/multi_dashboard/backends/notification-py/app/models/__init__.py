"""ORM models for notification-backend.

Import ``Base`` here so Alembic's env.py can reach all table metadata
via a single ``from app.models import Base`` import.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base — imported by Alembic env.py for autogenerate."""


# Import models so their tables are registered on Base.metadata
from .log import NotificationLog  # noqa: E402, F401
from .preference import UserPreference  # noqa: E402, F401

__all__ = ["Base", "UserPreference", "NotificationLog"]

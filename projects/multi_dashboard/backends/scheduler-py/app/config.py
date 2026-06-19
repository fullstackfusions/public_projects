"""Scheduler service settings.

Extends :class:`shared.config.AppSettings` with one service-specific field:
the PostgreSQL async connection URL.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from shared.config import AppSettings


class Settings(AppSettings):
    """All settings read from env / .env file."""

    service_name: str = "scheduler-backend"

    scheduler_database_url: str = Field(
        ...,
        description=(
            "Async PostgreSQL URL, e.g. "
            "postgresql+asyncpg://user:pass@host:5432/scheduler_db"
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # reads all fields from env


__all__ = ["Settings", "get_settings"]

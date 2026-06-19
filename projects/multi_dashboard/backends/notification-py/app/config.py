"""Notification service settings.

Extends :class:`shared.config.AppSettings` with channel-specific fields.
All secrets are read from the environment — never hardcoded.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from shared.config import AppSettings


class Settings(AppSettings):
    """All settings read from env / .env file."""

    service_name: str = "notification-backend"

    # PostgreSQL (asyncpg)
    notification_database_url: str = Field(
        ...,
        description="Async PostgreSQL URL, e.g. postgresql+asyncpg://user:pass@host/notification_db",
    )

    # SMTP — Mailpit locally, real SMTP in production (swap via env var only)
    smtp_host: str = Field("mailpit", description="SMTP server hostname")
    smtp_port: int = Field(1025, description="SMTP server port")
    smtp_from: str = Field("noreply@example.com", description="Sender address")
    smtp_username: str | None = Field(None, description="SMTP username (optional)")
    smtp_password: str | None = Field(None, description="SMTP password (optional)")

    # ntfy push
    ntfy_base_url: str = Field("http://ntfy", description="ntfy server base URL")

    # WAHA WhatsApp
    waha_base_url: str = Field("http://waha:3000", description="WAHA server base URL")
    waha_session: str = Field("default", description="WAHA session name")
    waha_api_key: str | None = Field(None, description="WAHA X-Api-Key header (leave empty to disable auth)")

    # Redis (DLQ) — DB 2 to avoid conflicts with auth (DB 1) and agentic-chat (DB 0)
    redis_url: str = Field("redis://redis:6379/2", description="Redis URL for DLQ")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings"]

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from shared.config import AppSettings


class Settings(AppSettings):
    service_name: str = "tax-backend"
    mongo_uri: str = Field(..., description="MongoDB connection URI")
    mongo_db: str = Field("tax_db", description="MongoDB database name")
    scheduler_api_url: str = Field(
        "http://scheduler-backend:8000",
        description="Base URL for the Scheduler API (used by setup-reminders)",
    )
    notification_api_url: str | None = Field(
        None,
        description="Base URL for the Notification API (optional; omit to disable notifications)",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings"]

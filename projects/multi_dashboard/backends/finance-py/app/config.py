from __future__ import annotations

from functools import lru_cache

from shared.config import AppSettings


class Settings(AppSettings):
    service_name: str = "finance-backend"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings"]

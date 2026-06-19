from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from shared.config import AppSettings


class Settings(AppSettings):
    service_name: str = "marketplace-backend"
    kafka_bootstrap: str = Field("localhost:9092")
    topic_orders_created: str = Field("orders.created")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings"]

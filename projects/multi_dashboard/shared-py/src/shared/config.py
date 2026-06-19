"""Base Pydantic Settings shared by all services.

Each backend subclasses :class:`AppSettings` and adds service-specific fields.

Example
-------
>>> # in backends/scheduler-py/app/config.py
>>> from shared.config import AppSettings
>>>
>>> class SchedulerSettings(AppSettings):
...     scheduler_database_url: str
...
>>> settings = SchedulerSettings()  # reads from environment / .env
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Literal, Tuple, Type

from pydantic import Field
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict


Environment = Literal["development", "staging", "production", "test"]


class _CsvFriendlyEnvSource(EnvSettingsSource):
    """Env source that accepts comma-separated strings for list[str] fields.

    pydantic-settings v2 tries to JSON-decode complex fields before Pydantic
    validators run, so ``CORS_ORIGINS=a,b`` would raise SettingsError.
    This subclass falls back to CSV split when JSON decoding fails.
    """

    def prepare_field_value(
        self,
        field_name: str,
        field: Any,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        # _field_is_complex mirrors the parent's internal check; value_is_complex
        # from the caller can be False for list[str] fields in pydantic-settings v2.
        is_complex, _ = self._field_is_complex(field)
        if (is_complex or value_is_complex) and isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return [item.strip() for item in value.split(",") if item.strip()]
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class AppSettings(BaseSettings):
    """Base settings every backend extends.

    Reads values from the process environment and an optional ``.env`` file in
    the working directory. Unknown extras are silently ignored so a single
    ``.env`` file can serve many services.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Identity
    service_name: str = Field(
        ...,
        description="Logical service name used in logs and error envelopes.",
    )
    environment: Environment = "development"

    # Logging
    log_level: str = "INFO"

    # CORS — comma-separated list of origins in env, parsed into a list here.
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins. In production, never use '*'.",
    )

    # JWT — every service shares this secret for local verification.
    auth_secret_key: str = Field(
        ...,
        description=(
            "HS256 shared secret. Set via env (AUTH_SECRET_KEY). "
            "All backends use the same value so any one can verify any token."
        ),
        min_length=16,
    )
    auth_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            _CsvFriendlyEnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings(settings_cls: type[AppSettings] = AppSettings) -> AppSettings:
    """Return a cached instance of the given settings class.

    Backends typically wrap this with their own factory to inject their
    subclass:

    >>> @lru_cache
    ... def get_scheduler_settings() -> SchedulerSettings:
    ...     return SchedulerSettings()
    """
    return settings_cls()  # type: ignore[call-arg]


__all__ = ["AppSettings", "Environment", "get_settings"]

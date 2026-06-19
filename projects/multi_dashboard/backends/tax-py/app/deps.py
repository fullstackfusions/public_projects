from __future__ import annotations

from typing import Any

from shared.auth import get_current_user_factory

from . import lifespan as _lifespan_mod
from .config import get_settings


def get_db() -> Any:
    """Return the shared AsyncDatabase instance. Used as a FastAPI dependency."""
    return _lifespan_mod.get_db()


get_current_user = get_current_user_factory(
    secret_provider=lambda: get_settings().auth_secret_key,
    algorithm="HS256",
)

__all__ = ["get_db", "get_current_user"]

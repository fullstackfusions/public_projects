from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from shared.config import AppSettings


class Settings(AppSettings):
    service_name: str = "auth-backend"

    # Database
    auth_database_url: str = Field(..., description="PostgreSQL asyncpg URL for users_db")

    # Token lifetimes (access_token_expire_minutes / refresh_token_expire_days
    # are inherited from AppSettings with the same defaults).

    # Google OAuth 2.0
    google_client_id: str = Field("", description="Google Cloud Console client ID")
    google_client_secret: str = Field("", description="Google Cloud Console client secret")
    google_redirect_uri: str = Field("http://localhost:8005/auth/google/callback")

    # Frontend redirect after OAuth (hash-fragment token delivery)
    frontend_redirect_uri: str = Field("http://localhost:5173/auth/callback")

    # Redis for OAuth state store
    redis_url: str = Field("redis://redis:6379/1")

    # Seed users: comma-separated "user:pass:role:email" entries
    seed_users: str = Field(
        "admin:admin123:admin:admin@example.com,"
        "demo:demo123:user:demo@example.com,"
        "user:user123:user:user@example.com"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings"]

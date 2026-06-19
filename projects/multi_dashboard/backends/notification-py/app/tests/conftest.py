"""Test fixtures for notification-backend.

Uses:
- aiosqlite in-memory SQLite (mimics Postgres schema)
- FakeRedis (in-process stub — no real Redis needed)
- shared.testing JWT minter for auth headers
- lifespan patching so tests don't need Docker
"""
from __future__ import annotations

import os
import warnings
from collections import defaultdict
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from shared.auth import encode_jwt
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Suppress the PendingDeprecationWarning from the `multipart` compat shim
# (shipped by python-multipart ≤0.0.9) that old starlette (≤0.37) triggers
# via `import multipart`. This is a third-party packaging concern, not our
# code — must be filtered before any FastAPI/starlette import fires the warning.
# None of the imports above pull in starlette, so suppressing here still
# precedes the `from app.*` imports below that do.
warnings.filterwarnings(
    "ignore", category=PendingDeprecationWarning, module=r"multipart.*"
)

# ── Test constants ─────────────────────────────────────────────────────────────

TEST_SECRET = "test-secret-key-at-least-32-chars-long"
TEST_USER_ID = "test-user-123"

# Inject required env vars BEFORE the Settings class is first instantiated.
# This covers every module that calls get_settings() — no per-module patching needed.
_TEST_ENV = {
    "AUTH_SECRET_KEY": TEST_SECRET,
    "NOTIFICATION_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "SERVICE_NAME": "notification-backend",
    "ENVIRONMENT": "test",
    "LOG_LEVEL": "WARNING",
    "CORS_ORIGINS": "http://localhost:5173",
    "SMTP_HOST": "localhost",
    "SMTP_PORT": "1025",
    "SMTP_FROM": "test@example.com",
    "NTFY_BASE_URL": "http://ntfy",
    "WAHA_BASE_URL": "http://waha:3000",
    "WAHA_SESSION": "default",
    "REDIS_URL": "redis://localhost/2",
}

for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

# Clear the lru_cache so get_settings() re-reads our env vars (not a stale
# cached instance from a previous import).
from app.config import get_settings as _get_settings  # noqa: E402

_get_settings.cache_clear()

from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402

# ── In-memory SQLite DB ────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# ── Fake Redis stub ────────────────────────────────────────────────────────────

class FakeRedis:
    """Minimal in-process stub that satisfies the dispatcher's Redis usage."""

    def __init__(self) -> None:
        self._lists: dict[str, list[str]] = defaultdict(list)

    async def ping(self) -> bool:
        return True

    async def lpush(self, key: str, *values: str) -> int:
        self._lists[key].extend(values)
        return len(self._lists[key])

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self._lists[key]
        return items[start : None if end == -1 else end + 1]

    async def aclose(self) -> None:
        pass


@pytest.fixture()
def fake_redis() -> FakeRedis:
    return FakeRedis()


# ── JWT helper ─────────────────────────────────────────────────────────────────

def make_token(sub: str = TEST_USER_ID, role: str = "user") -> str:
    return encode_jwt({"sub": sub, "role": role}, TEST_SECRET, "HS256", expires_in_seconds=300)


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token()}"}


# ── Full ASGI test client ──────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def client(db_session: Any, fake_redis: FakeRedis) -> AsyncClient:
    """Return an AsyncClient wired to a patched app (SQLite + FakeRedis)."""
    from app import lifespan as ls_module

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Wire the test engine + FakeRedis into the lifespan singletons so no
    # real Postgres or Redis connection is needed.
    with (
        patch.object(ls_module, "_session_factory", factory),
        patch.object(ls_module, "_engine", engine),
        patch.object(ls_module, "_redis", fake_redis),
    ):
        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    await engine.dispose()

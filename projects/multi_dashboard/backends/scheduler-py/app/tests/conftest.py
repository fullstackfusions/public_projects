"""pytest fixtures for scheduler-backend tests.

Uses in-memory SQLite via aiosqlite (same SQLAlchemy 2 async API as asyncpg,
but no external DB needed for CI). JWT is minted offline — no auth-backend needed.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

# Set env BEFORE importing app modules so Settings validation passes.
os.environ.setdefault("SERVICE_NAME", "scheduler-backend")
os.environ.setdefault("SCHEDULER_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-min16chars")
# CORS_ORIGINS: use JSON array syntax for pydantic-settings list[str] parsing
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')

from httpx import ASGITransport, AsyncClient
from shared.auth import encode_jwt
from shared.db.sql import make_async_engine, make_async_session_factory

import app.lifespan as _lifespan_mod
from app.main import app
from app.models import Base

# ── In-memory SQLite engine / session factory ─────────────────────────────────

@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = make_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session_factory(db_engine):
    return make_async_session_factory(db_engine)


# ── Patch lifespan module globals so deps.get_db works ────────────────────────

@pytest_asyncio.fixture(scope="function", autouse=True)
async def patch_session_factory(db_session_factory):
    """Inject the in-memory session factory into the lifespan module."""
    _lifespan_mod._session_factory = db_session_factory
    yield
    _lifespan_mod._session_factory = None


# ── Async HTTP client bound to the ASGI app ───────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── JWT helpers ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def auth_token() -> str:
    return encode_jwt(
        {"sub": "test-user", "email": "test@example.com", "role": "user"},
        secret="test-secret-key-min16chars",
        expires_in_seconds=3600,
    )


@pytest.fixture(scope="session")
def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}

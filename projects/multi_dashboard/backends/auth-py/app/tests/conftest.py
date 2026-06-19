"""Test configuration for auth-py.

Uses SQLite (aiosqlite) in-memory database to avoid a real Postgres dependency.
Patches lifespan module globals directly so tests bypass the real lifespan context.
"""
from __future__ import annotations

import os
import uuid

# Set env vars BEFORE importing app modules so Settings() doesn't fail.
os.environ.setdefault("AUTH_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-min16chars!!")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SEED_USERS", "")
os.environ.setdefault("GOOGLE_CLIENT_ID", "")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from shared.auth import encode_jwt
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.lifespan as _lifespan_mod
from app.main import create_app
from app.models import Base


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db() -> None:  # type: ignore[misc]
    """Create in-memory SQLite tables and patch lifespan singletons."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    _lifespan_mod._engine = engine  # type: ignore[assignment]
    _lifespan_mod._session_factory = factory  # type: ignore[assignment]
    _lifespan_mod._redis = _FakeRedis()

    yield  # type: ignore[misc]

    _lifespan_mod._engine = None
    _lifespan_mod._session_factory = None
    _lifespan_mod._redis = None
    await engine.dispose()


class _FakeRedis:
    """Minimal in-process Redis stub for OAuth state tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def ping(self) -> None:
        pass

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value

    async def getdel(self, key: str) -> str | None:
        return self._store.pop(key, None)

    async def aclose(self) -> None:
        pass


@pytest.fixture()
def app_client():  # type: ignore[misc]
    return create_app()


@pytest_asyncio.fixture()
async def client(app_client):  # type: ignore[misc]
    async with AsyncClient(
        transport=ASGITransport(app=app_client), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    secret = os.environ["AUTH_SECRET_KEY"]
    token = encode_jwt(
        {"sub": str(uuid.uuid4()), "email": "test@example.com", "role": "user"},
        secret,
        "HS256",
        expires_in_seconds=300,
    )
    return {"Authorization": f"Bearer {token}"}

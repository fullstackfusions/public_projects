"""Test configuration for tax-backend.

Injects an in-memory mongomock-motor database in place of the real AsyncMongoClient,
bypassing the lifespan entirely — no live MongoDB needed for smoke tests.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

# Set env vars BEFORE any app module is imported so Settings() sees them.
os.environ.setdefault("SERVICE_NAME", "tax-backend")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "tax_db_test")
os.environ.setdefault("SCHEDULER_API_URL", "http://scheduler-backend:8000")
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-min16chars")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient  # type: ignore[import-untyped]
from shared.auth import encode_jwt

import app.lifespan as _lifespan_mod
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="function", autouse=True)
async def patch_mongo_db() -> AsyncIterator[None]:
    """Replace the lifespan-managed AsyncMongoClient with an in-memory mock."""
    mock_client = AsyncMongoMockClient()
    _lifespan_mod._client = mock_client  # type: ignore[assignment]
    _lifespan_mod._db = mock_client["tax_db_test"]  # type: ignore[assignment]
    yield
    _lifespan_mod._client = None
    _lifespan_mod._db = None


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


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

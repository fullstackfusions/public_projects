"""FastAPI TestClient fixtures."""
from __future__ import annotations


import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def async_client_factory():
    """Returns a factory that builds an :class:`httpx.AsyncClient` bound to a
    FastAPI app::

        async def test_health(async_client_factory):
            async with async_client_factory(app) as client:
                resp = await client.get("/")
                assert resp.status_code == 200
    """

    def _factory(app, base_url: str = "http://test") -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=app), base_url=base_url)

    return _factory


__all__ = ["async_client_factory"]

"""Smoke tests for the tax-backend service.

Covers: health probes, auth gate, corporation CRUD, and error envelope shape.
No live MongoDB needed — mongomock-motor is injected via conftest.py.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Health probes
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_ready(client: AsyncClient) -> None:
    # mongomock-motor client doesn't implement admin.command("ping"),
    # so /ready falls through to the except branch — 503 is acceptable here.
    resp = await client.get("/ready")
    assert resp.status_code in (200, 503)


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_list_corporations_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/corporations")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "UNAUTHORIZED"
    assert "trace_id" in body


# ---------------------------------------------------------------------------
# Corporation CRUD
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_list_corporations_empty(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/corporations", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_create_corporation(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "name": "Acme Corp",
        "corp_number": "1234567",
        "fiscal_year_end_month": 12,
        "incorporation_date": "2020-01-15",
    }
    resp = await client.post("/corporations", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Acme Corp"
    assert "id" in body


@pytest.mark.anyio
async def test_read_corporation(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # Create first
    payload = {
        "name": "Read Corp",
        "fiscal_year_end_month": 3,
        "incorporation_date": "2019-06-01",
    }
    create_resp = await client.post("/corporations", json=payload, headers=auth_headers)
    assert create_resp.status_code == 201
    corp_id = create_resp.json()["id"]

    # Read back
    resp = await client.get(f"/corporations/{corp_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == corp_id
    assert body["name"] == "Read Corp"
    assert body["filings"] == []


@pytest.mark.anyio
async def test_update_corporation(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "name": "Update Corp",
        "fiscal_year_end_month": 6,
        "incorporation_date": "2021-03-10",
    }
    create_resp = await client.post("/corporations", json=payload, headers=auth_headers)
    corp_id = create_resp.json()["id"]

    resp = await client.put(
        f"/corporations/{corp_id}",
        json={"name": "Updated Corp"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Corp"


@pytest.mark.anyio
async def test_delete_corporation(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "name": "Delete Corp",
        "fiscal_year_end_month": 9,
        "incorporation_date": "2018-11-20",
    }
    create_resp = await client.post("/corporations", json=payload, headers=auth_headers)
    corp_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/corporations/{corp_id}", headers=auth_headers)
    assert del_resp.status_code == 204


# ---------------------------------------------------------------------------
# Error envelope shape
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_not_found_returns_envelope(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # Valid ObjectId format but doesn't exist
    fake_id = "000000000000000000000000"
    resp = await client.get(f"/corporations/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "NOT_FOUND"
    assert "trace_id" in body
    assert "message" in body


@pytest.mark.anyio
async def test_invalid_corp_id_returns_404_envelope(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/corporations/not-a-valid-objectid", headers=auth_headers)
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "NOT_FOUND"
    assert "trace_id" in body

"""Smoke tests for auth-backend.

10 tests covering health, auth gate, password CRUD, token flows, error envelopes.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready(client: AsyncClient) -> None:
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_me_no_token_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert "code" in body
    assert "trace_id" in body


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert "id" in body


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_422(client: AsyncClient) -> None:
    payload = {"email": "bob@example.com", "password": "password123"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 422
    assert "code" in resp.json()


@pytest.mark.asyncio
async def test_token_valid_credentials(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "charlie@example.com", "password": "hunter2abc"},
    )
    resp = await client.post(
        "/auth/token",
        data={"username": "charlie@example.com", "password": "hunter2abc"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_token_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "eve@example.com", "password": "correcthorse"},
    )
    resp = await client.post(
        "/auth/token",
        data={"username": "eve@example.com", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401
    assert "code" in resp.json()


@pytest.mark.asyncio
async def test_me_with_valid_token(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "dave@example.com", "password": "securepass1"},
    )
    tok_resp = await client.post(
        "/auth/token",
        data={"username": "dave@example.com", "password": "securepass1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    access = tok_resp.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "dave@example.com"


@pytest.mark.asyncio
async def test_refresh_token_issues_new_access_token(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "frank@example.com", "password": "refreshtest1"},
    )
    tok_resp = await client.post(
        "/auth/token",
        data={"username": "frank@example.com", "password": "refreshtest1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    refresh = tok_resp.json()["refresh_token"]
    resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_token_unknown_user_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/token",
        data={"username": "nobody@example.com", "password": "anything"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body.get("code") == "UNAUTHORIZED"

"""Smoke tests for notification-backend.

Covers:
1. /health → 200
2. /notify → 401 without token (envelope shape)
3. /notify with valid token → email adapter called (mocked SMTP)
4. /notify/template dedup: second call with same dedup_key → skipped
5. GET /preferences/me → auto-creates blank row
6. PUT /preferences/me → updates channels
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from .conftest import TEST_USER_ID, make_token


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_notify_direct_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/notify",
        json={
            "user_id": "u1",
            "channel": "email",
            "to": "a@b.com",
            "subject": "hi",
            "body": "hello",
        },
    )
    assert resp.status_code == 401
    body = resp.json()
    assert "code" in body  # ErrorEnvelope shape


@pytest.mark.asyncio
async def test_notify_direct_email_ok(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {make_token()}"}
    with patch(
        "app.domain.adapters.email.aiosmtplib.send",
        new_callable=AsyncMock,
        return_value=({}, ""),
    ):
        resp = await client.post(
            "/notify",
            json={
                "user_id": TEST_USER_ID,
                "channel": "email",
                "to": "user@example.com",
                "subject": "Tax Reminder",
                "body": "Your T2 is due.",
            },
            headers=headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["status"] == "sent"


@pytest.mark.asyncio
async def test_preferences_get_creates_blank(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {make_token()}"}
    resp = await client.get("/preferences/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == TEST_USER_ID
    assert body["enabled_channels"] == []


@pytest.mark.asyncio
async def test_preferences_put(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {make_token()}"}
    resp = await client.put(
        "/preferences/me",
        json={"email": "me@example.com", "enabled_channels": ["email"]},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@example.com"
    assert body["enabled_channels"] == ["email"]


@pytest.mark.asyncio
async def test_template_dispatch_dedup(client: AsyncClient) -> None:
    """Second call with same dedup_key should be skipped, not re-sent."""
    headers = {"Authorization": f"Bearer {make_token()}"}

    # Set up preferences first so the dispatcher has something to fan out to
    await client.put(
        "/preferences/me",
        json={"email": "me@example.com", "enabled_channels": ["email"]},
        headers=headers,
    )

    payload = {
        "user_id": TEST_USER_ID,
        "template_id": "tax_deadline",
        "dedup_key": "tax_deadline_u1_2025_t2_90",
        "context": {"corp_name": "Acme Inc", "days_before": 90},
    }

    with patch(
        "app.domain.adapters.email.aiosmtplib.send",
        new_callable=AsyncMock,
        return_value=({}, ""),
    ):
        r1 = await client.post("/notify/template", json=payload, headers=headers)
        r2 = await client.post("/notify/template", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200

    r1_result = r1.json()["results"][0]
    r2_result = r2.json()["results"][0]

    assert r1_result["status"] == "sent"
    assert r2_result["status"] == "skipped"

"""Smoke tests for scheduler-backend.

Covers:
  1. /health → 200 liveness
  2. /ready  → 200 readiness (in-memory DB is always up)
  3. /events → 401 envelope without token (CWE-306 gate)
  4. /events → 200 with valid token (no data yet = empty page)
  5. POST /events → 201 creates event
  6. GET  /events/{id} → 200 returns event
  7. PUT  /events/{id} → 200 updates event
  8. DELETE /events/{id} → 204 removes event
  9. GET  /events/{id} → 404 envelope after delete
  10. POST /reminders → 404 envelope when event_id missing
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_health(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_ready(client: AsyncClient) -> None:
    r = await client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


async def test_events_no_token_returns_401_envelope(client: AsyncClient) -> None:
    r = await client.get("/events")
    assert r.status_code == 401
    body = r.json()
    assert "code" in body
    assert "message" in body
    assert "trace_id" in body


async def test_events_list_with_token(client: AsyncClient, auth_headers: dict) -> None:
    r = await client.get("/events", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_create_event(client: AsyncClient, auth_headers: dict) -> None:
    payload = {
        "title": "Team Standup",
        "start_time": "2026-06-01T09:00:00",
        "end_time": "2026-06-01T09:30:00",
    }
    r = await client.post("/events", json=payload, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Team Standup"
    assert "id" in body


async def test_read_event(client: AsyncClient, auth_headers: dict) -> None:
    # Create first
    payload = {
        "title": "Read Event Test",
        "start_time": "2026-06-02T10:00:00",
        "end_time": "2026-06-02T11:00:00",
    }
    create_r = await client.post("/events", json=payload, headers=auth_headers)
    event_id = create_r.json()["id"]

    r = await client.get(f"/events/{event_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == event_id
    assert r.json()["reminders"] == []


async def test_update_event(client: AsyncClient, auth_headers: dict) -> None:
    payload = {
        "title": "Original",
        "start_time": "2026-06-03T10:00:00",
        "end_time": "2026-06-03T11:00:00",
    }
    event_id = (await client.post("/events", json=payload, headers=auth_headers)).json()["id"]

    r = await client.put(f"/events/{event_id}", json={"title": "Updated"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Updated"


async def test_delete_event_and_404(client: AsyncClient, auth_headers: dict) -> None:
    payload = {
        "title": "Delete Me",
        "start_time": "2026-06-04T10:00:00",
        "end_time": "2026-06-04T11:00:00",
    }
    event_id = (await client.post("/events", json=payload, headers=auth_headers)).json()["id"]

    del_r = await client.delete(f"/events/{event_id}", headers=auth_headers)
    assert del_r.status_code == 204

    get_r = await client.get(f"/events/{event_id}", headers=auth_headers)
    assert get_r.status_code == 404
    body = get_r.json()
    assert body["code"] == "NOT_FOUND"
    assert "trace_id" in body


async def test_create_reminder_bad_event_404(client: AsyncClient, auth_headers: dict) -> None:
    payload = {
        "message": "Remind me",
        "remind_at": "2026-06-01T08:00:00",
        "event_id": 999999,
    }
    r = await client.post("/reminders", json=payload, headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"

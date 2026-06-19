"""Liveness and readiness probes.

GET /health  — liveness:  always 200 {"status": "ok"}
GET /ready   — readiness: 200 when DB and Redis are reachable, 503 otherwise
"""
from __future__ import annotations

import sqlalchemy
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..lifespan import get_redis_client, get_session_factory

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always returns 200."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    """Readiness probe — 200 when DB and Redis are both reachable, 503 otherwise."""
    errors: list[str] = []

    # DB check
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(sqlalchemy.text("SELECT 1"))
    except Exception as exc:
        errors.append(f"db: {exc}")

    # Redis check
    try:
        redis = get_redis_client()
        await redis.ping()
    except Exception as exc:
        errors.append(f"redis: {exc}")

    if errors:
        return JSONResponse({"status": "unavailable", "detail": errors}, status_code=503)
    return JSONResponse({"status": "ready"})


__all__ = ["router"]

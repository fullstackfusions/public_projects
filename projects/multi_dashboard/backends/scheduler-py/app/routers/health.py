"""Liveness and readiness probes.

GET /health  — liveness:  always 200 {"status": "ok"}
GET /ready   — readiness: 200 when DB is reachable, 503 otherwise
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..lifespan import get_session_factory

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always returns 200."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    """Readiness probe — 200 when DB is reachable, 503 otherwise."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready"})
    except Exception as exc:
        return JSONResponse({"status": "unavailable", "detail": str(exc)}, status_code=503)


__all__ = ["router"]

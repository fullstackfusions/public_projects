from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    # Kafka liveness is best-effort; producer start already validated in lifespan
    return JSONResponse({"status": "ready"})

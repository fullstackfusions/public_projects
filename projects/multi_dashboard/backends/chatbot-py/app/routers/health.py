from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@router.get("/ready")
async def ready() -> JSONResponse:
    return JSONResponse({"status": "ready"})

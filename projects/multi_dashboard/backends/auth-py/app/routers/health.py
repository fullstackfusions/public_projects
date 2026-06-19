from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import lifespan as _lifespan_mod

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    try:
        engine = _lifespan_mod.get_engine()
        async with engine.connect() as conn:
            await conn.run_sync(lambda c: None)
        redis = _lifespan_mod.get_redis()
        await redis.ping()
        return JSONResponse({"status": "ready"})
    except Exception as exc:
        return JSONResponse({"status": "unavailable", "detail": str(exc)}, status_code=503)

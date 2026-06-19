"""Application lifespan: start / stop the async DB engine.

FastAPI wires this in via ``app = FastAPI(lifespan=lifespan)``.
The session factory is stored as a module-level singleton so deps.py can
call :func:`get_session_factory` without needing ``app.state``.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.db.sql import make_async_engine, make_async_session_factory
from shared.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from .config import get_settings

logger = get_logger(__name__)

# Module-level singletons — populated at startup, cleared at shutdown.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory is not initialised. Did the lifespan run?")
    return _session_factory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: create engine + session factory. Shutdown: dispose engine."""
    global _engine, _session_factory

    settings = get_settings()
    logger.info("Connecting to database", extra={"url": settings.scheduler_database_url.split("@")[-1]})

    _engine = make_async_engine(settings.scheduler_database_url)
    _session_factory = make_async_session_factory(_engine)

    # Verify connectivity with a startup ping (DB startup retry handled by
    # Compose healthcheck / service restart policy).
    try:
        async with _engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed at startup", extra={"error": str(exc)})
        raise

    yield  # ── application runs here ──────────────────────────────────────────

    logger.info("Shutting down database engine")
    await _engine.dispose()
    _engine = None
    _session_factory = None


__all__ = ["lifespan", "get_session_factory"]

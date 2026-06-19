"""Application lifespan: start / stop the async DB engine and Redis client.

FastAPI wires this in via ``app = FastAPI(lifespan=lifespan)``.
Singletons are stored at module level so deps.py can access them without
needing ``app.state``.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import sqlalchemy
from fastapi import FastAPI
from shared.db.sql import make_async_engine, make_async_session_factory
from shared.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from .config import get_settings

logger = get_logger(__name__)

# Module-level singletons — populated at startup, cleared at shutdown.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis: aioredis.Redis | None = None  # type: ignore[type-arg]


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Did the lifespan run?")
    return _session_factory


def get_redis_client() -> aioredis.Redis:  # type: ignore[type-arg]
    if _redis is None:
        raise RuntimeError("Redis client not initialised. Did the lifespan run?")
    return _redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: connect DB + Redis. Shutdown: dispose both."""
    global _engine, _session_factory, _redis

    settings = get_settings()

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    db_host = settings.notification_database_url.split("@")[-1]
    logger.info("Connecting to database", extra={"url": db_host})
    _engine = make_async_engine(settings.notification_database_url)
    _session_factory = make_async_session_factory(_engine)

    try:
        async with _engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed at startup", extra={"error": str(exc)})
        raise

    # ── Redis ─────────────────────────────────────────────────────────────────
    logger.info("Connecting to Redis", extra={"url": settings.redis_url})
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await _redis.ping()
        logger.info("Redis connection verified")
    except Exception as exc:
        logger.error("Redis ping failed at startup", extra={"error": str(exc)})
        raise

    yield  # ── application runs here ──────────────────────────────────────────

    logger.info("Shutting down")
    await _engine.dispose()
    await _redis.aclose()
    _engine = None
    _session_factory = None
    _redis = None


__all__ = ["lifespan", "get_session_factory", "get_redis_client"]

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI
from shared.db.sql import make_async_engine, make_async_session_factory
from shared.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from .config import get_settings
from .seed import seed_users

logger = get_logger(__name__)

# Module-level singletons
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[Any] | None = None
_redis: Any = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("DB engine not initialised. Did lifespan run?")
    return _engine


def get_session_factory() -> async_sessionmaker[Any]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Did lifespan run?")
    return _session_factory


def get_redis() -> Any:
    if _redis is None:
        raise RuntimeError("Redis client not initialised. Did lifespan run?")
    return _redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _engine, _session_factory, _redis

    settings = get_settings()
    logger.info("Starting auth-backend", extra={"db": settings.auth_database_url[:30]})

    _engine = make_async_engine(settings.auth_database_url)
    _session_factory = make_async_session_factory(_engine)

    # Verify DB connectivity
    async with _engine.begin() as conn:
        await conn.run_sync(lambda c: None)
    logger.info("Database connection verified")

    # Redis for OAuth state
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
    await _redis.ping()
    logger.info("Redis connection verified")

    # Seed default users
    async with _session_factory() as session, session.begin():
        await seed_users(session, settings.seed_users)

    yield

    logger.info("Shutting down auth-backend")
    await _redis.aclose()
    await _engine.dispose()
    _engine = None
    _session_factory = None
    _redis = None


__all__ = ["lifespan", "get_engine", "get_session_factory", "get_redis"]

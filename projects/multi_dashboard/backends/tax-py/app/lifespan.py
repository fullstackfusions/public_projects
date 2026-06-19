from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pymongo import ASCENDING
from shared.db.mongo import get_database, make_async_mongo_client
from shared.logging import get_logger

from .config import get_settings

logger = get_logger(__name__)

# Module-level singletons — populated at startup, cleared at shutdown.
_client: Any = None
_db: Any = None


def get_db() -> Any:
    if _db is None:
        raise RuntimeError("MongoDB not initialised. Did lifespan run?")
    return _db


def get_client() -> Any:
    if _client is None:
        raise RuntimeError("MongoDB client not initialised. Did lifespan run?")
    return _client


async def _create_indexes(db: Any) -> None:
    """Create all required MongoDB indexes. Idempotent — safe to call on every startup."""
    corps = db["corporations"]
    filings = db["tax_filing_records"]
    nil_t2 = db["nil_t2_reports"]

    await corps.create_index([("name", ASCENDING)])

    await filings.create_index([("corp_id", ASCENDING)])
    await filings.create_index([("due_date", ASCENDING)])
    await filings.create_index(
        [("corp_id", ASCENDING), ("filing_type", ASCENDING), ("period_label", ASCENDING)],
        unique=True,
    )

    await nil_t2.create_index([("corp_id", ASCENDING)])
    await nil_t2.create_index(
        [("corp_id", ASCENDING), ("fiscal_year_end", ASCENDING)],
        unique=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: connect AsyncMongoClient + create indexes. Shutdown: close client."""
    global _client, _db

    settings = get_settings()
    logger.info("Connecting to MongoDB", extra={"db": settings.mongo_db})

    _client = make_async_mongo_client(settings.mongo_uri, app_name=settings.service_name)
    _db = get_database(_client, settings.mongo_db)

    try:
        await _client.admin.command("ping")
        logger.info("MongoDB connection verified")
    except Exception as exc:
        logger.error("MongoDB ping failed at startup", extra={"error": str(exc)})
        raise

    await _create_indexes(_db)

    yield  # ── application runs here ──────────────────────────────────────────

    logger.info("Shutting down MongoDB client")
    _client.close()
    _client = None
    _db = None


__all__ = ["lifespan", "get_db", "get_client"]

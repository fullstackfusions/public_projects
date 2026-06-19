from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from shared.logging import get_logger

from .config import get_settings
from .kafka_client import make_producer

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.kafka_producer = await make_producer(settings.kafka_bootstrap)
    logger.info("Kafka producer connected", extra={"bootstrap": settings.kafka_bootstrap})
    yield
    await app.state.kafka_producer.stop()
    logger.info("Kafka producer stopped")

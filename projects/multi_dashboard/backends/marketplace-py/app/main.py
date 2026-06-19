from __future__ import annotations

from fastapi import FastAPI
from shared.cors import add_cors
from shared.errors import register_exception_handlers
from shared.middleware import install_middleware

from .config import get_settings
from .lifespan import lifespan
from .routers import health, orders


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Marketplace API",
        version="1.0.0",
        description="Contract-first marketplace API with Kafka event publishing",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    install_middleware(app)
    register_exception_handlers(app)
    add_cors(app, settings.cors_origins)

    app.include_router(health.router)
    app.include_router(orders.router)

    return app


app = create_app()

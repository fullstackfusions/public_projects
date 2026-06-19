"""Scheduler backend — application factory.

This file is intentionally thin (≤80 LOC):
  - create FastAPI instance with lifespan
  - install shared middleware + error handlers
  - configure CORS
  - mount routers

Business logic lives in routers/, crud/, schemas/, models/.
"""
from __future__ import annotations

from fastapi import FastAPI
from shared.cors import add_cors
from shared.errors import register_exception_handlers
from shared.middleware import install_middleware

from .config import get_settings
from .lifespan import lifespan
from .routers import events, health, reminders


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Scheduler API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Shared cross-cutting concerns
    install_middleware(app)
    register_exception_handlers(app)
    add_cors(app, settings.cors_origins)

    # Route registration
    app.include_router(health.router)
    app.include_router(events.router)
    app.include_router(reminders.router)

    # TODO: add /metrics Prometheus endpoint (Phase observability pass)

    return app


app = create_app()

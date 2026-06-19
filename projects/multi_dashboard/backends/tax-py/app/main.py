"""Tax backend — application factory.

Thin entry point: wires shared middleware, error handlers, CORS, and routers.
Business logic lives in routers/, crud/, schemas/, models/, services/, domain/.

# TODO: add /metrics Prometheus endpoint (planned — see refactor-plan.md §6.4)
"""
from __future__ import annotations

from fastapi import FastAPI
from shared.cors import add_cors
from shared.errors import register_exception_handlers
from shared.middleware import install_middleware

from .config import get_settings
from .lifespan import lifespan
from .routers import corporations, filings, health, nil_t2


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Tax API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    install_middleware(app)
    register_exception_handlers(app)
    add_cors(app, settings.cors_origins)
    app.include_router(health.router)
    app.include_router(corporations.router)
    app.include_router(filings.router)
    app.include_router(nil_t2.router)
    return app


app = create_app()

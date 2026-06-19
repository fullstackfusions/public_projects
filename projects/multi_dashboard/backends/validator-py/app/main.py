from __future__ import annotations

from fastapi import FastAPI
from shared.cors import add_cors
from shared.errors import register_exception_handlers
from shared.middleware import install_middleware

from .config import get_settings
from .routers import health, stream, validate


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Validator API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    install_middleware(app)
    register_exception_handlers(app)
    add_cors(app, settings.cors_origins)

    app.include_router(health.router)
    app.include_router(validate.router)
    app.include_router(stream.router)

    return app


app = create_app()

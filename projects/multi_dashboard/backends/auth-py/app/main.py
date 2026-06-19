from __future__ import annotations

from fastapi import FastAPI
from shared.cors import add_cors
from shared.errors import register_exception_handlers
from shared.middleware import install_middleware

from .config import get_settings
from .lifespan import lifespan
from .routers import auth, health, oauth

# TODO: Add /metrics Prometheus endpoint (observability pass)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Auth API",
        version="2.0.0",
        description="JWT authentication + Google OAuth 2.0",
        lifespan=lifespan,
    )
    install_middleware(app)
    register_exception_handlers(app)
    add_cors(app, settings.cors_origins)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(oauth.router)

    return app


app = create_app()

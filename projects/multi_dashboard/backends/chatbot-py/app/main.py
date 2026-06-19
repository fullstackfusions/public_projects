from __future__ import annotations

from fastapi import FastAPI
from shared.cors import add_cors
from shared.errors import register_exception_handlers
from shared.middleware import install_middleware

from .config import get_settings
from .routers import chat, health, sse, ws


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Chatbot API",
        version="1.0.0",
        description="WebSocket, REST, and SSE chat demo",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    install_middleware(app)
    register_exception_handlers(app)
    add_cors(app, settings.cors_origins)

    app.include_router(health.router)
    app.include_router(ws.router)
    app.include_router(chat.router)
    app.include_router(sse.router)

    return app


app = create_app()

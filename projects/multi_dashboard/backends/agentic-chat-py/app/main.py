from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, FastAPI
from shared.auth import get_current_user_factory
from shared.cors import add_cors
from shared.errors import NotFoundError, register_exception_handlers
from shared.logging import get_logger
from shared.middleware import install_middleware

from .agents.central import CentralAgent
from .config import get_settings
from .models import AgentStep, MessageRequest, MessageResponse, MessageStatus, MessageStatusResponse
from .redis_store import job_store

logger = get_logger(__name__)

settings = get_settings()

get_current_user = get_current_user_factory(
    secret_provider=lambda: settings.auth_secret_key,
    algorithm="HS256",
)

_router = APIRouter()


async def _run_agent(msg_id: str, query: str, conversation_id: str) -> None:
    async def status_callback(agent: str, action: str, detail: str | None) -> None:
        step = AgentStep(agent=agent, action=action, detail=detail)
        await job_store.add_step(msg_id, step.model_dump())

    try:
        central = CentralAgent(
            llm_provider=settings.default_llm_provider,
            model_name=settings.default_model,
        )
        result = await central.run(
            query=query,
            thread_id=conversation_id,
            status_callback=status_callback,
        )
        await job_store.complete_job(msg_id, result)
    except Exception as exc:
        logger.exception("Agent run failed for msg_id=%s", msg_id, exc_info=exc)
        await job_store.fail_job(msg_id, str(exc))


@_router.post("/message", response_model=MessageResponse)
async def post_message(
    request: MessageRequest,
    _user=Depends(get_current_user),
) -> MessageResponse:
    msg_id = str(uuid.uuid4())
    conversation_id = request.conversation_id or str(uuid.uuid4())

    await job_store.create_job(msg_id, conversation_id)
    asyncio.create_task(_run_agent(msg_id, request.message, conversation_id))

    return MessageResponse(
        msg_id=msg_id,
        conversation_id=conversation_id,
        status=MessageStatus.processing,
    )


@_router.get("/message/{msg_id}", response_model=MessageStatusResponse)
async def get_message_status(msg_id: str) -> MessageStatusResponse:
    job = await job_store.get_job(msg_id)
    if not job:
        raise NotFoundError("Message not found")
    return MessageStatusResponse(**job)


@_router.get("/health")
async def health() -> dict:
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@_router.get("/ready")
async def ready() -> dict:
    return {"status": "ready"}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agentic Chat API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    install_middleware(app)
    register_exception_handlers(app)
    add_cors(app, settings.cors_origins)

    app.include_router(_router)

    return app


app = create_app()

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from shared.auth import get_current_user_factory
from shared.errors import NotFoundError

from ..config import get_settings
from ..domain import generate_random_response, get_random_delay, get_random_status
from ..schemas.chat import ChatMessage, ChatRequest, ChatResponse
from ..store import conversations, pending_responses

router = APIRouter(prefix="/api", tags=["chat-rest"])

get_current_user = get_current_user_factory(
    secret_provider=lambda: get_settings().auth_secret_key,
    algorithm="HS256",
)


@router.post("/chat", response_model=ChatResponse)
async def rest_chat(request: ChatRequest, _user=Depends(get_current_user)) -> ChatResponse:
    conversation_id = request.conversation_id or str(uuid.uuid4())

    user_msg = ChatMessage(role="user", content=request.message)
    conversations.setdefault(conversation_id, []).append(user_msg)

    await asyncio.sleep(get_random_delay() * 2)

    response_content = generate_random_response()
    assistant_msg = ChatMessage(role="assistant", content=response_content)
    conversations[conversation_id].append(assistant_msg)

    return ChatResponse(message=assistant_msg, conversation_id=conversation_id)


@router.post("/chat/async")
async def rest_chat_async(request: ChatRequest, _user=Depends(get_current_user)) -> dict:
    conversation_id = request.conversation_id or str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    user_msg = ChatMessage(role="user", content=request.message)
    conversations.setdefault(conversation_id, []).append(user_msg)

    pending_responses[request_id] = {
        "status": "pending",
        "statuses": [],
        "conversation_id": conversation_id,
        "response": None,
        "created_at": datetime.now().isoformat(),
    }

    asyncio.create_task(_process_async_request(request_id, conversation_id))

    return {
        "request_id": request_id,
        "conversation_id": conversation_id,
        "status": "processing",
        "timestamp": datetime.now().isoformat(),
    }


async def _process_async_request(request_id: str, conversation_id: str) -> None:
    try:
        num_status_updates = random.randint(2, 5)
        for i in range(num_status_updates):
            status = get_random_status()
            pending_responses[request_id]["statuses"].append(
                {
                    "status": status,
                    "progress": int((i + 1) / num_status_updates * 100),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            pending_responses[request_id]["status"] = "processing"
            await asyncio.sleep(get_random_delay() / num_status_updates)

        response_content = generate_random_response()
        assistant_msg = ChatMessage(role="assistant", content=response_content)
        conversations[conversation_id].append(assistant_msg)

        pending_responses[request_id]["status"] = "complete"
        pending_responses[request_id]["response"] = assistant_msg.model_dump()
    except Exception as exc:
        pending_responses[request_id]["status"] = "error"
        pending_responses[request_id]["error"] = str(exc)


@router.get("/chat/status/{request_id}")
async def get_chat_status(request_id: str) -> dict:
    if request_id not in pending_responses:
        raise NotFoundError("Request not found")
    return pending_responses[request_id]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    if conversation_id not in conversations:
        raise NotFoundError("Conversation not found")
    return {
        "conversation_id": conversation_id,
        "messages": [msg.model_dump() for msg in conversations[conversation_id]],
    }


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str) -> dict:
    conversations.pop(conversation_id, None)
    return {"message": "Conversation cleared"}

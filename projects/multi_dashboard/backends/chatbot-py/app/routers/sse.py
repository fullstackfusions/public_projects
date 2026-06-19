from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from shared.auth import get_current_user_factory

from ..config import get_settings
from ..domain import (
    generate_random_response,
    get_random_chunk_delay,
    get_random_delay,
    get_random_status,
)
from ..schemas.chat import ChatMessage, ChatRequest
from ..store import conversations

router = APIRouter(prefix="/api", tags=["chat-sse"])

get_current_user = get_current_user_factory(
    secret_provider=lambda: get_settings().auth_secret_key,
    algorithm="HS256",
)


@router.post("/chat/stream")
async def sse_chat(request: ChatRequest, _user=Depends(get_current_user)) -> StreamingResponse:
    conversation_id = request.conversation_id or str(uuid.uuid4())

    user_msg = ChatMessage(role="user", content=request.message)
    conversations.setdefault(conversation_id, []).append(user_msg)

    async def generate_sse():  # type: ignore[return]
        try:
            event_data = {
                "type": "received",
                "message_id": user_msg.id,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
            }
            yield f"event: received\ndata: {json.dumps(event_data)}\n\n"

            num_statuses = random.randint(2, 5)
            for i in range(num_statuses):
                event_data = {
                    "type": "status",
                    "status": get_random_status(),
                    "progress": int((i + 1) / num_statuses * 100),
                    "timestamp": datetime.now().isoformat(),
                }
                yield f"event: status\ndata: {json.dumps(event_data)}\n\n"
                await asyncio.sleep(get_random_delay() / num_statuses)

            full_response = generate_random_response()
            words = full_response.split()
            accumulated = ""

            for i, word in enumerate(words):
                accumulated += word + " "
                event_data = {
                    "type": "chunk",
                    "content": accumulated.strip(),
                    "is_final": i == len(words) - 1,
                    "timestamp": datetime.now().isoformat(),
                }
                yield f"event: chunk\ndata: {json.dumps(event_data)}\n\n"
                await asyncio.sleep(get_random_chunk_delay())

            assistant_msg = ChatMessage(role="assistant", content=full_response)
            conversations[conversation_id].append(assistant_msg)

            event_data = {
                "type": "complete",
                "content": full_response,
                "message_id": assistant_msg.id,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
            }
            yield f"event: complete\ndata: {json.dumps(event_data)}\n\n"

        except Exception as exc:
            event_data = {"type": "error", "content": str(exc), "timestamp": datetime.now().isoformat()}
            yield f"event: error\ndata: {json.dumps(event_data)}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

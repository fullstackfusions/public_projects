from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..domain import (
    generate_random_response,
    get_random_chunk_delay,
    get_random_delay,
    get_random_status,
)
from ..schemas.chat import ChatMessage
from ..store import conversations

router = APIRouter(tags=["chat-ws"])


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    conversation_id = str(uuid.uuid4())

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            user_message = message_data.get("message", "")
            conv_id = message_data.get("conversation_id", conversation_id)

            if not user_message:
                await websocket.send_json(
                    {"type": "error", "content": "Empty message received", "timestamp": datetime.now().isoformat()}
                )
                continue

            user_msg = ChatMessage(role="user", content=user_message)
            conversations.setdefault(conv_id, []).append(user_msg)

            await websocket.send_json(
                {
                    "type": "received",
                    "message_id": user_msg.id,
                    "conversation_id": conv_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            num_statuses = random.randint(2, 5)
            for i in range(num_statuses):
                await websocket.send_json(
                    {
                        "type": "status",
                        "status": get_random_status(),
                        "progress": int((i + 1) / num_statuses * 100),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                await asyncio.sleep(get_random_delay() / num_statuses)

            full_response = generate_random_response()
            words = full_response.split()
            accumulated = ""

            for i, word in enumerate(words):
                accumulated += word + " "
                await websocket.send_json(
                    {
                        "type": "chunk",
                        "content": accumulated.strip(),
                        "is_final": i == len(words) - 1,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                await asyncio.sleep(get_random_chunk_delay())

            assistant_msg = ChatMessage(role="assistant", content=full_response)
            conversations[conv_id].append(assistant_msg)

            await websocket.send_json(
                {
                    "type": "complete",
                    "content": full_response,
                    "message_id": assistant_msg.id,
                    "conversation_id": conv_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json(
                {"type": "error", "content": str(exc), "timestamp": datetime.now().isoformat()}
            )
        except Exception:
            pass

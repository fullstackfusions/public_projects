from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: ChatMessage
    conversation_id: str


class StatusUpdate(BaseModel):
    type: str
    status: Optional[str] = None
    content: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

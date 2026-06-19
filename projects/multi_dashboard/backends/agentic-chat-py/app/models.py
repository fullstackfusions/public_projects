from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageStatus(str, Enum):
    processing = "processing"
    complete = "complete"
    error = "error"


class AgentStep(BaseModel):
    agent: str
    action: str  # "started" | "tool_called" | "completed" | "error"
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class MessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class MessageResponse(BaseModel):
    msg_id: str
    conversation_id: str
    status: MessageStatus = MessageStatus.processing
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class MessageStatusResponse(BaseModel):
    msg_id: str
    conversation_id: str
    status: MessageStatus
    steps: List[AgentStep] = []
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

from __future__ import annotations

from typing import Dict, List

from .schemas.chat import ChatMessage

# In-memory state — intentionally module-level (single process, no persistence needed)
pending_responses: Dict[str, dict] = {}
conversations: Dict[str, List[ChatMessage]] = {}

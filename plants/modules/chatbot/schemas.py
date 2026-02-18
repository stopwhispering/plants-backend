from __future__ import annotations

from typing import List, Dict, Optional, Literal, Any
from datetime import datetime
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "bot"]
    text: str
    timestamp: datetime


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[ChatMessage]
    reasoning: Optional[str] = None
    plant_ids: list[int]

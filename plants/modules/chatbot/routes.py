from __future__ import annotations

import logging
from typing import Any, List, Dict
import uuid

from fastapi import APIRouter

from .schemas import ChatMessage, ChatRequest, ChatResponse
from .api import get_chat_reply

logger = logging.getLogger(__name__)

# Router for a small, in-memory chatbot with dummy replies
router = APIRouter(
    tags=["chatbot"],
    responses={404: {"description": "Not found"}},
)


# Very small in-memory store for sessions. This is not persistent and only for development/demo use.
_sessions: Dict[str, List[ChatMessage]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Any:
    """Accepts a user message, stores it in a session and returns a reply from the agent.

    This endpoint now calls the LangChain/Groq-backed agent when available and falls back to a dummy reply.
    """
    session_id = request.session_id or str(uuid.uuid4())

    hist = _sessions.setdefault(session_id, [])

    # call the chat API which will call the agent/llm and optionally tools
    reply_data = await get_chat_reply(
        request.message,
        history=hist,
        session_id=session_id,
        # allow_tools=True
    )

    # ensure we use the returned history (which includes added messages)
    new_history: List[ChatMessage] = reply_data.get("history", hist)
    _sessions[session_id] = new_history

    return ChatResponse(
            session_id=session_id,
            reply=reply_data.get("reply", ""),
            reasoning=reply_data.get("reasoning", ""),
            plant_ids=reply_data.get("plant_ids", []),
            history=new_history,
            # tool_results=reply_data.get("tool_results"),
        )


@router.get("/chat/history/{session_id}", response_model=List[ChatMessage])
async def get_history(session_id: str) -> List[ChatMessage]:
    """Return the stored conversation history for a session_id (or empty list)."""
    return _sessions.get(session_id, [])

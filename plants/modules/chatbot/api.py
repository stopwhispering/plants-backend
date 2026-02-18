from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .agent import ChatAgent
from .schemas import ChatMessage

logger = logging.getLogger(__name__)

_agent = ChatAgent()


async def get_chat_reply(
        message: str,
        history: Optional[List[ChatMessage]] = None,
        session_id: Optional[str] = None,
        # allow_tools: bool = True
) -> Dict[str, Any]:
    """Public helper to get a chatbot reply. Returns dict with keys: session_id, reply, tool_results, history"""
    if history is None:
        history = []

    # ensure timestamps are timezone-aware
    reply = await _agent.ask(message, history)

    # append messages locally (the routes module may also do this; keep it idempotent)
    now = datetime.now(timezone.utc)
    user_msg = ChatMessage(role="user", text=message, timestamp=now)
    # bot_msg = ChatMessage(role="bot", text=reply.get('text'), timestamp=datetime.now(timezone.utc))
    bot_msg = ChatMessage(role="bot", text=reply.message, timestamp=datetime.now(timezone.utc))
    history = history + [user_msg, bot_msg]

    return {
        "session_id": session_id or "",
        # "reply": reply.get('text'),
        "reply": reply.message,
        # "reasoning": reply.get('reasoning'),
        "reasoning": reply.reasoning,
        # "tool_results": tool_results,
        "history": history,
        "plant_ids": reply.plant_ids,
    }

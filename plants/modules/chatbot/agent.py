from __future__ import annotations

import logging
import os
from textwrap import dedent
from typing import Any, List

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, SystemMessage, BaseMessage, HumanMessage

from langchain_groq import ChatGroq  # type: ignore
from langchain.agents import create_agent
from langgraph.types import Command
from pydantic import BaseModel

from plants.modules.chatbot.schemas import ChatMessage
from plants.modules.chatbot.tools.registry import get_langchain_tools

# from .schemas import ChatMessage
# from .tools import get_langchain_tools

logger = logging.getLogger(__name__)


class PlantQueryResponse(BaseModel):
    """Plant Query Output Schema for structured output parsing of agent responses."""
    message: str
    plant_ids: list[int]
    reasoning: str = None


SYSTEM_PROMPT = dedent("""\
You are an assistant for answering questions about the user's plant collection.
You can call external tools to retrieve plant details, events, and florescence data.

OUTPUT FORMAT (MANDATORY):
Return ONLY a valid JSON string that strictly matches this schema:
{
  "message": string,
  "plant_ids": number[]
}

ABSOLUTE RULES:
- Always include BOTH fields: "message" and "plant_ids"
- Do NOT include any extra keys
- Do NOT include explanations, comments, or text outside the JSON string
- The JSON string must be syntactically valid

MESSAGE FIELD RULES:
- "message" is user-facing natural language formatted as HTML
- Do NOT use HTML headers (<h1>–<h6>)
- Keep responses concise and clear
- If your answer contains a list, render it as an HTML list. Include details in parentheses.
- Don't return HTML tables but lists.

PLANT DATA RULES:
- Do NOT answer plant-specific questions from your own knowledge
- When returning plant information:
  - Include plant names, their IDs and all other plant details you got from the tools in the HTML message
  - Include only the corresponding numeric IDs in "plant_ids"

ERROR HANDLING:
- If a tool call fails or returns an error, return the error message as the "message"
- In error cases, still include "plant_ids"

GENERAL:
- Keep all responses concise
- You do NOT need a tool to construct the JSON itself. Just return the JSON string.
""")


async def _build_messages(
        user_message: str,
        history: List[ChatMessage]
        # ) -> List[Dict[str, str]]:
) -> list[BaseMessage]:
    # messages: List[Dict[str, str]] = []
    # messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

    # include history as user/bot messages
    for m in history:
        # role = "user" if m.role == "user" else "assistant"
        # messages.append({"role": role, "content": m.text})
        if m.role == "user":
            messages.append(HumanMessage(content=m.text))
        else:
            messages.append(AIMessage(content=m.text))

    # append the new user message
    messages.append(HumanMessage(content=user_message))
    # messages.append({"role": "user", "content": user_message})
    return messages


class ChatAgent:
    def __init__(
            self,
    ):
        tools = get_langchain_tools()
        self.agent = GroqLLM(tools=tools)

    async def ask(
            self,
            user_message: str,
            history: List[ChatMessage],
    ) -> PlantQueryResponse:
        """Get a reply for the given user_message. Returns dict with keys: reply, tool_results (optional)."""
        messages = await _build_messages(user_message, history)

        # LangChain agent invocation - uses agent.ainvoke for async agent call
        try:
            response = await self.agent.chat(messages)

            return response

        except Exception as exc:
            logger.exception(f"Agent invocation failed: {exc}")
            return PlantQueryResponse(
                message=f"(fallback) I couldn't reach the LLM: {str(exc)}",
                plant_ids=[],
                reasoning=""
            )


class GroqLLM:
    def __init__(self, tools: list[Any]):
        # ChatGroq expects the API key to be set in the environment variable GROQ_API_KEY.
        model = os.getenv("CHATBOT_MODEL") or "openai/gpt-oss-20b"
        llm = ChatGroq(model=model)

        self._client = create_agent(
            llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )

    async def chat(
            self,
            # messages: List[Dict[str, str]]
            messages: List[BaseMessage]
    ) -> PlantQueryResponse:
        """Send messages to the model and return the assistant reply text.
        messages: list of dicts like {"role": "system|user|assistant", "content": "..."}
        """
        # call the langgraph agent with the full message history and get the
        # full message history including tool calls and final response
        try:
            response = await self._client.ainvoke(
                Command(
                    update={
                        "messages": messages
                    }
                )
            )
        except Exception as exc:
            logger.exception(f"{exc}")
            raise exc

        final_response = response['messages'][-1]
        parsed = PlantQueryResponse.model_validate_json(final_response.text)
        parsed.reasoning = final_response.additional_kwargs['reasoning_content'] if 'reasoning_content' in final_response.additional_kwargs else None
        return parsed

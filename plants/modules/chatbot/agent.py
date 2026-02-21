from __future__ import annotations

import logging
import os
from textwrap import dedent
from typing import Any, List

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
    You are an assistant answering questions about the user's plants collection. You may call external tools
    to retrieve plants in the user's collection.
    
    You MUST return your final answer as valid JSON string matching this schema:
    {
      "message": string,
      "plant_ids": number[]
    }
    
    Rules:
    - Always include both fields
    - message is user-facing natural language as HTML code. Don't use headers.
    - plant_ids is a list of integers
    - Do not include any extra keys
    - Do not include explanations outside JSON
    - You do not need any tool for creating the JSON, just return the JSON as a string in your final response.
    - If the user asks for a plant or multiple plants, use the tools to get the information instead of answering from your own knowledge
      and return both the plant names and their ids in the message part, formatted as HTML, and the ids in the plant_ids list.
    - Keep responses concise.
    - If a tool fails or returns an error, return the error message in the message field.
    - If the user asks for a plant, consider the supplied plant name the botanical name.
    - Prefer HTML tables or lists if returning multiple plants, but keep it simple and concise.
    
)""")


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
            a = 1

        final_response = response['messages'][-1]
        parsed = PlantQueryResponse.model_validate_json(final_response.text)
        parsed.reasoning = final_response.additional_kwargs['reasoning_content'] if 'reasoning_content' in final_response.additional_kwargs else None
        return parsed

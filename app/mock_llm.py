"""Deterministic CrewAI BaseLLM mock for offline tool-calling smoke tests."""

from __future__ import annotations

import json
import re
from typing import Any

from crewai.llms.base_llm import BaseLLM
from crewai.tools.base_tool import BaseTool
from crewai.utilities.types import LLMMessage
from pydantic import BaseModel

_RECORD_ID_RE = re.compile(r"NYK-SMOKE-\d{3}")


def _normalize_messages(messages: str | list[LLMMessage]) -> list[dict[str, str]]:
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    normalized: list[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, dict):
            role = str(msg.get("role", "user"))
            content = msg.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            normalized.append({"role": role, "content": content})
    return normalized


def _assistant_observation_text(messages: list[dict[str, str]]) -> str | None:
    """Return tool observation text from assistant turns only (not system templates)."""
    for msg in reversed(messages):
        if msg["role"] != "assistant":
            continue
        text = msg["content"]
        idx = text.rfind("\nObservation:")
        if idx == -1:
            continue
        observation = text[idx + len("\nObservation:") :].strip()
        if observation and "the result of the action" not in observation:
            return observation
    return None


def _extract_record_id(messages: list[dict[str, str]]) -> str:
    for msg in reversed(messages):
        if msg["role"] not in ("user", "assistant"):
            continue
        match = _RECORD_ID_RE.search(msg["content"])
        if match:
            return match.group(0)
    return "NYK-SMOKE-001"


def _tool_has_record_id_param(tool_entry: Any) -> tuple[str, str] | None:
    """Select tool by declared argument schema (record_id), not by name substring."""
    tool_obj: Any | None = None
    tool_name: str | None = None

    if isinstance(tool_entry, dict):
        for key, value in tool_entry.items():
            if hasattr(value, "name"):
                tool_obj = value
                tool_name = getattr(value, "name", None) or str(key)
                break
    elif hasattr(tool_entry, "name"):
        tool_obj = tool_entry
        tool_name = tool_obj.name

    if tool_obj is None:
        return None

    args_schema = getattr(tool_obj, "args_schema", None)
    if args_schema is not None:
        schema = args_schema.model_json_schema()
        props = schema.get("properties", {})
        if "record_id" in props:
            return tool_name or tool_obj.name, "record_id"

    func = getattr(tool_obj, "func", None) or getattr(tool_obj, "_run", None)
    if func is not None and hasattr(func, "__annotations__"):
        if "record_id" in func.__annotations__:
            return tool_name or tool_obj.name, "record_id"

    return None


def _resolve_order_lookup_tool(
    tools: list[dict[str, BaseTool]] | None,
    available_functions: dict[str, Any] | None,
    from_agent: Any | None = None,
) -> tuple[str, str] | None:
    if tools:
        for entry in tools:
            match = _tool_has_record_id_param(entry)
            if match:
                return match

    agent_tools = getattr(from_agent, "tools", None) if from_agent is not None else None
    if agent_tools:
        for entry in agent_tools:
            match = _tool_has_record_id_param(entry)
            if match:
                return match

    if available_functions:
        for name, fn in available_functions.items():
            if hasattr(fn, "__annotations__") and "record_id" in fn.__annotations__:
                return name, "record_id"
            tool_attr = getattr(fn, "args_schema", None)
            if tool_attr is not None:
                props = tool_attr.model_json_schema().get("properties", {})
                if "record_id" in props:
                    return name, "record_id"
    return None


class MockCrewLLM(BaseLLM):
    """Offline CrewAI LLM that drives ReAct tool calls using schema-aware dispatch."""

    model: str = "mock-crew-llm"
    provider: str = "mock"
    call_count: int = 0

    def call(
        self,
        messages: str | list[LLMMessage],
        tools: list[dict[str, BaseTool]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> str | Any:
        self.call_count += 1
        normalized = _normalize_messages(messages)
        observation = _assistant_observation_text(normalized)

        if observation:
            return (
                "Thought: The lookup tool returned real computed JSON.\n"
                f"Final Answer: Order lookup result: {observation}"
            )

        tool_match = _resolve_order_lookup_tool(tools, available_functions, from_agent)
        if tool_match is None:
            return (
                "Thought: No order lookup tool with record_id schema is available.\n"
                "Final Answer: Unable to perform order lookup in smoke mode."
            )

        tool_name, arg_name = tool_match
        record_id = _extract_record_id(normalized)
        action_input = json.dumps({arg_name: record_id})
        return (
            "Thought: I must call the order lookup tool using its record_id schema.\n"
            f"Action: {tool_name}\n"
            f"Action Input: {action_input}"
        )

    async def acall(
        self,
        messages: str | list[LLMMessage],
        tools: list[dict[str, BaseTool]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> str | Any:
        return self.call(
            messages,
            tools=tools,
            callbacks=callbacks,
            available_functions=available_functions,
            from_task=from_task,
            from_agent=from_agent,
            response_model=response_model,
        )

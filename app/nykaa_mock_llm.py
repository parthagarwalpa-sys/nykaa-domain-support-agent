"""Task 7 deterministic CrewAI BaseLLM — routes RAG vs order lookup by tool schema and query."""

from __future__ import annotations

import json
import re
from typing import Any

from crewai.llms.base_llm import BaseLLM
from crewai.tools.base_tool import BaseTool
from crewai.utilities.types import LLMMessage
from pydantic import BaseModel

from app.crew_schemas import SupportCrewResponse
from app.mock_llm import _assistant_observation_text, _normalize_messages
from app.structured_output import build_support_crew_response_from_traces

_RECORD_ID_RE = re.compile(r"NYK-20261013-\d{4}")


def _latest_user_text(messages: list[dict[str, str]]) -> str:
    for msg in reversed(messages):
        if msg["role"] == "user":
            return msg["content"]
    return messages[-1]["content"] if messages else ""


def _extract_record_id(messages: list[dict[str, str]]) -> str | None:
    for msg in reversed(messages):
        if msg["role"] not in ("user", "assistant"):
            continue
        match = _RECORD_ID_RE.search(msg["content"])
        if match:
            return match.group(0)
    return None


def _tool_schema_properties(tool_obj: Any) -> dict[str, Any]:
    args_schema = getattr(tool_obj, "args_schema", None)
    if args_schema is None:
        return {}
    return args_schema.model_json_schema().get("properties", {})


def _iter_agent_tools(from_agent: Any | None) -> list[Any]:
    if from_agent is None:
        return []
    tools = getattr(from_agent, "tools", None) or []
    return list(tools)


def _find_tool_by_schema(from_agent: Any | None, field_name: str) -> tuple[str, str] | None:
    for tool_obj in _iter_agent_tools(from_agent):
        name = getattr(tool_obj, "name", None)
        props = _tool_schema_properties(tool_obj)
        if field_name in props and name:
            return name, field_name
    return None


def _is_order_status_query(text: str) -> bool:
    lowered = text.lower()
    return _RECORD_ID_RE.search(text) is not None and any(
        token in lowered for token in ("order", "status", "check", "lookup", "track")
    )


def _is_policy_query(text: str) -> bool:
    if _is_order_status_query(text):
        return False
    lowered = text.lower()
    policy_hints = (
        "policy",
        "return",
        "refund",
        "delivery",
        "cancel",
        "exchange",
        "warranty",
        "cod",
        "beauty",
        "eligible",
        "timeline",
        "sla",
    )
    return any(hint in lowered for hint in policy_hints)


def _collect_observation_payloads(messages: list[dict[str, str]]) -> list[str]:
    payloads: list[str] = []
    for msg in messages:
        content = msg["content"]
        if "Observation:" not in content:
            continue
        observation = content.split("Observation:", 1)[-1].strip()
        if observation and "the result of the action" not in observation:
            payloads.append(observation)
    return payloads


class NykaaMockCrewLLM(BaseLLM):
    """Offline CrewAI LLM for three-agent support crew tool routing."""

    model: str = "nykaa-mock-crew-llm"
    provider: str = "mock"
    call_count: int = 0

    def supports_function_calling(self) -> bool:
        # Keep ReAct Action/Action Input tool routing for tool-equipped agents.
        return False

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
        user_text = _latest_user_text(normalized)
        observation = _assistant_observation_text(normalized)
        agent_tools = _iter_agent_tools(from_agent)

        if response_model is not None and not agent_tools:
            built = build_support_crew_response_from_traces()
            if isinstance(response_model, type) and issubclass(response_model, SupportCrewResponse):
                return built.model_dump_json()
            return response_model.model_validate(built.model_dump()).model_dump_json()

        if not agent_tools and any(msg["role"] == "system" for msg in normalized):
            # CrewAI output converter path (post-compose structured validation).
            built = build_support_crew_response_from_traces()
            return built.model_dump_json()

        if observation and agent_tools:
            return (
                "Thought: Tool returned real JSON from the registered backend.\n"
                f"Final Answer: {observation}"
            )

        if not agent_tools:
            observations = _collect_observation_payloads(normalized)
            if not observations:
                combined = " ".join(msg["content"] for msg in normalized if msg["role"] != "system")
                return (
                    "Thought: Compose a draft using upstream agent outputs only.\n"
                    f"Final Answer: {combined.strip()}"
                )
            merged = " | ".join(observations)
            return (
                "Thought: Compose final draft strictly from tool observations.\n"
                f"Final Answer: {merged}"
            )

        rag_tool = _find_tool_by_schema(from_agent, "policy_question")
        order_tool = _find_tool_by_schema(from_agent, "record_id")

        if rag_tool and _is_policy_query(user_text):
            tool_name, arg_name = rag_tool
            action_input = json.dumps({arg_name: user_text.strip()})
            return (
                "Thought: Policy question detected; call RAG tool using policy_question schema.\n"
                f"Action: {tool_name}\n"
                f"Action Input: {action_input}"
            )

        if order_tool and _is_order_status_query(user_text):
            record_id = _extract_record_id(normalized)
            if record_id:
                tool_name, arg_name = order_tool
                action_input = json.dumps({arg_name: record_id})
                return (
                    "Thought: Order status query detected; call lookup tool using record_id schema.\n"
                    f"Action: {tool_name}\n"
                    f"Action Input: {action_input}"
                )

        if rag_tool:
            return (
                "Thought: No policy retrieval required for this request.\n"
                "Final Answer: Retrieval skipped — not a policy question."
            )

        if order_tool:
            return (
                "Thought: No order record_id present for lookup.\n"
                "Final Answer: Order lookup skipped — no record_id in query."
            )

        return (
            "Thought: No schema-matched tool available.\n"
            "Final Answer: No tool action taken."
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

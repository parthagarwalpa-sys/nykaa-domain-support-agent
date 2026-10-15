"""Deterministic AutoGen ChatCompletionClient for offline structured review smoke tests."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator, Mapping, Sequence
from typing import Any, Literal

from autogen_core import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    ModelCapabilities,
    ModelFamily,
    ModelInfo,
    RequestUsage,
)
from autogen_core.models._types import LLMMessage
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel

from app.schemas import ReviewVerdict

_UNGROUNDED_MARKERS = (
    "lifetime warranty on all electronics",
    "UNGROUNDED_CLAIM",
)


def _flatten_message_text(messages: Sequence[LLMMessage]) -> str:
    parts: list[str] = []
    for msg in messages:
        content = getattr(msg, "content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts.append(str(content))
    return "\n".join(parts)


def _extract_section(text: str, label: str) -> str:
    pattern = rf"{label}:\s*(.*?)(?:\n[A-Z][a-z_ ]+:|$)"
    match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _derive_corrected_answer(context: str) -> str:
    """Build a revision from supplied source context (not a fixed sentence map)."""
    cleaned = context.strip()
    if not cleaned:
        return "I cannot verify unsupported claims against the supplied source context."
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if sentences:
        return "Based on the provided source context only: " + " ".join(sentences[:2])
    return "Based on the provided source context only: " + cleaned[:400]


def _token_overlap_ratio(left: str, right: str) -> float:
    left_tokens = {t for t in re.findall(r"[a-z0-9]+", left.lower()) if len(t) > 2}
    right_tokens = {t for t in re.findall(r"[a-z0-9]+", right.lower()) if len(t) > 2}
    if not left_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens)


def _draft_is_ungrounded(draft: str, context: str) -> bool:
    lowered_draft = draft.lower()
    lowered_context = context.lower()
    if any(marker.lower() in lowered_draft for marker in _UNGROUNDED_MARKERS):
        return True
    if "lifetime warranty" in lowered_draft and "lifetime warranty" not in lowered_context:
        return True
    if _normalize_text(draft) in _normalize_text(context):
        return False
    if _token_overlap_ratio(draft, context) >= 0.45:
        return False
    # Explicit unsupported claim pattern for revision demos only.
    if "unlimited" in lowered_draft and "unlimited" not in lowered_context:
        return True
    return False


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


class DeterministicMockChatCompletionClient(ChatCompletionClient):
    """Schema-aware offline model client; no API keys or remote inference."""

    def __init__(self) -> None:
        self.create_call_count = 0
        self._usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    @property
    def model_info(self) -> ModelInfo:
        return {
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "structured_output": True,
            "family": ModelFamily.UNKNOWN,
        }

    @property
    def capabilities(self) -> ModelCapabilities:
        return {
            "vision": False,
            "function_calling": True,
            "json_output": True,
        }

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: bool | type[BaseModel] | None = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: CancellationToken | None = None,
    ) -> CreateResult:
        del tools, tool_choice, extra_create_args, cancellation_token
        self.create_call_count += 1
        blob = _flatten_message_text(messages)
        draft = _extract_section(blob, "Draft answer") or _extract_section(blob, "Draft")
        context = (
            _extract_section(blob, "Retrieved policy context")
            or _extract_section(blob, "Retrieved context")
            or _extract_section(blob, "Context")
        )
        order_lookup = _extract_section(blob, "Verified order lookup")
        if order_lookup and order_lookup != "N/A":
            context = f"{context}\n{order_lookup}".strip()

        if isinstance(json_output, type) and issubclass(json_output, BaseModel):
            ungrounded = _draft_is_ungrounded(draft, context)
            if ungrounded:
                corrected = _derive_corrected_answer(context)
                verdict = ReviewVerdict(
                    approved=False,
                    final_answer=corrected,
                    reason="Removed or corrected claims not supported by retrieved context.",
                )
            else:
                verdict = ReviewVerdict(
                    approved=True,
                    final_answer=draft,
                    reason="Draft aligns with supplied retrieved context.",
                )
            content = verdict.model_dump_json()
        else:
            ungrounded = _draft_is_ungrounded(draft, context)
            if ungrounded:
                content = (
                    "Policy review: the draft includes statements not supported by the "
                    "retrieved context. Recommend revision before release."
                )
            else:
                content = (
                    "Policy review: the draft appears consistent with the retrieved context."
                )

        self._usage = RequestUsage(
            prompt_tokens=self._usage.prompt_tokens + max(len(blob) // 4, 1),
            completion_tokens=self._usage.completion_tokens + max(len(content) // 4, 1),
        )
        return CreateResult(
            finish_reason="stop",
            content=content,
            usage=RequestUsage(prompt_tokens=len(blob) // 4, completion_tokens=len(content) // 4),
            cached=False,
        )

    def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: bool | type[BaseModel] | None = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[str | CreateResult, None]:
        async def _stream() -> AsyncGenerator[str | CreateResult, None]:
            result = await self.create(
                messages,
                tools=tools,
                tool_choice=tool_choice,
                json_output=json_output,
                extra_create_args=extra_create_args,
                cancellation_token=cancellation_token,
            )
            yield result

        return _stream()

    async def close(self) -> None:
        return None

    def actual_usage(self) -> RequestUsage:
        return self._usage

    def total_usage(self) -> RequestUsage:
        return self._usage

    def count_tokens(
        self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []
    ) -> int:
        del tools
        return max(len(_flatten_message_text(messages)) // 4, 1)

    def remaining_tokens(
        self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []
    ) -> int:
        return max(4096 - self.count_tokens(messages, tools=tools), 0)

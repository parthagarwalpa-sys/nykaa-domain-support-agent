"""Part 2 Task 8 — in-process LangChain session memory."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# In-process only: session_id -> LangChain history (not persisted across restarts).
_SESSION_STORE: dict[str, InMemoryChatMessageHistory] = {}

_ORDER_JSON_RE = re.compile(r"\{[^{}]*\"record_id\"\s*:\s*\"NYK-20261013-\d{4}\"[^{}]*\}")


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """LangChain session history factory used by RunnableWithMessageHistory."""
    if session_id not in _SESSION_STORE:
        _SESSION_STORE[session_id] = InMemoryChatMessageHistory()
    return _SESSION_STORE[session_id]


def list_session_ids() -> list[str]:
    return sorted(_SESSION_STORE.keys())


def session_store_summary() -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for session_id in list_session_ids():
        history = _SESSION_STORE[session_id]
        summary[session_id] = {
            "message_count": len(history.messages),
            "messages": [
                {"type": message.type, "content": message.content}
                for message in history.messages
            ],
        }
    return summary


def clear_session(session_id: str) -> None:
    _SESSION_STORE.pop(session_id, None)


def reset_all_sessions() -> None:
    _SESSION_STORE.clear()


def history_message_count(session_id: str) -> int:
    return len(get_session_history(session_id).messages)


def serialize_history_messages(messages: list[BaseMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        role = "User" if isinstance(message, HumanMessage) else "Assistant"
        lines.append(f"{role}: {message.content}")
    return "\n".join(lines)


def extract_order_payload_from_messages(messages: list[BaseMessage]) -> dict[str, Any] | None:
    """Parse the most recent order lookup JSON embedded in assistant history."""
    for message in reversed(messages):
        if not isinstance(message, AIMessage):
            continue
        content = message.content
        if not isinstance(content, str):
            continue
        marker = "ORDER_LOOKUP_JSON="
        if marker in content:
            json_part = content.split(marker, 1)[1].strip()
            try:
                payload = json.loads(json_part)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and payload.get("record_id"):
                return payload
        for match in _ORDER_JSON_RE.finditer(content):
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
            if "escalation_recommended" in payload and "record_id" in payload:
                return payload
    return None


def is_escalation_follow_up(user_text: str) -> bool:
    lowered = user_text.lower()
    return "escalat" in lowered or "need escalation" in lowered

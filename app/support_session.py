"""Task 8 — LangChain session memory wired to the Task 7 support crew."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory

from app.memory import (
    extract_order_payload_from_messages,
    get_session_history,
    is_escalation_follow_up,
    reset_all_sessions,
    serialize_history_messages,
    session_store_summary,
)
from app.guardrails import run_guarded_support_crew_kickoff

MISSING_ORDER_CONTEXT_RESPONSE = (
    "I don't have a prior order lookup in this conversation session. "
    "Please provide an order ID or ask about a specific order first."
)

TURN1_ORDER_QUERY = "Check the status of order NYK-20261013-0005."
TURN2_ESCALATION_QUERY = "Is it likely to need escalation?"


def _append_order_context(output: str, crew_result: dict[str, Any]) -> str:
    if not crew_result.get("order_tool_trace"):
        return output
    payload = crew_result["order_tool_trace"][0]["payload"]
    return output + "\n\nORDER_LOOKUP_JSON=" + json.dumps(payload, sort_keys=True)


def _build_crew_query(user_input: str, prior_messages: list[BaseMessage]) -> str:
    if not prior_messages:
        return user_input
    history_block = serialize_history_messages(prior_messages)
    return (
        "Use the prior conversation context below when answering the current message.\n"
        f"{history_block}\n\n"
        f"Current customer message: {user_input}"
    )


def _turn_metadata_from_crew(crew_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "guardrail_blocked": bool(crew_result.get("guardrail_blocked")),
        "guardrail_type": crew_result.get("guardrail_type"),
        "guardrail_reason": crew_result.get("guardrail_reason"),
        "governance_outcome": crew_result.get("governance_outcome"),
        "estimated_budget_tokens": crew_result.get("estimated_budget_tokens"),
        "budget_cap_tokens": crew_result.get("budget_cap_tokens"),
        "sanitized_request_length": crew_result.get("sanitized_request_length"),
        "kickoff_used": bool(crew_result.get("kickoff_used")),
        "sanitized_query": crew_result.get("sanitized_query"),
        "phone_masks_applied": int(crew_result.get("phone_masks_applied") or 0),
        "structured_response": crew_result.get("structured_response"),
        "rag_tool_call_count": crew_result.get("rag_tool_call_count"),
        "order_tool_call_count": crew_result.get("order_tool_call_count"),
        "autogen_review": crew_result.get("autogen_review"),
    }


def _support_turn(inputs: dict[str, Any]) -> dict[str, Any]:
    user_input = str(inputs["input"]).strip()
    prior_messages: list[BaseMessage] = list(inputs.get("history") or [])

    if is_escalation_follow_up(user_input) and not prior_messages:
        return {
            "output": MISSING_ORDER_CONTEXT_RESPONSE,
            "guardrail_blocked": False,
            "kickoff_used": False,
            "structured_response": None,
        }

    if is_escalation_follow_up(user_input) and prior_messages:
        prior_order = extract_order_payload_from_messages(prior_messages)
        if prior_order is not None:
            recommended = prior_order["escalation_recommended"]
            score = prior_order["escalation_score"]
            record_id = prior_order["record_id"]
            if recommended:
                answer = (
                    f"Based on the earlier lookup for {record_id} in this session "
                    f"(escalation_score={score}, threshold crossed), escalation is recommended."
                )
            else:
                answer = (
                    f"Based on the earlier lookup for {record_id} in this session "
                    f"(escalation_score={score}), escalation is not recommended."
                )
            return {
                "output": answer,
                "guardrail_blocked": False,
                "kickoff_used": False,
                "structured_response": None,
            }

    crew_query = _build_crew_query(user_input, prior_messages)
    crew_result = run_guarded_support_crew_kickoff(crew_query)
    meta = _turn_metadata_from_crew(crew_result)
    if crew_result.get("guardrail_blocked"):
        return {
            "output": str(crew_result.get("assistant_refusal", "Request blocked by guardrails.")),
            **meta,
        }
    output = _append_order_context(crew_result["kickoff_output"], crew_result)
    return {"output": output, **meta}


def build_session_chat_runnable() -> RunnableWithMessageHistory:
    base = RunnableLambda(_support_turn)
    return RunnableWithMessageHistory(
        base,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )


def run_session_turn(session_id: str, user_message: str) -> dict[str, Any]:
    runnable = build_session_chat_runnable()
    config = {"configurable": {"session_id": session_id}}
    prior_count = len(get_session_history(session_id).messages)
    prior_history_snapshot = serialize_history_messages(get_session_history(session_id).messages)

    result = runnable.invoke({"input": user_message}, config=config)
    if isinstance(result, dict):
        output = str(result.get("output", ""))
        turn_meta = {k: result.get(k) for k in (
            "guardrail_blocked",
            "guardrail_type",
            "guardrail_reason",
            "governance_outcome",
            "estimated_budget_tokens",
            "budget_cap_tokens",
            "sanitized_request_length",
            "kickoff_used",
            "sanitized_query",
            "phone_masks_applied",
            "structured_response",
            "rag_tool_call_count",
            "order_tool_call_count",
            "autogen_review",
        )}
    else:
        output = str(result)
        turn_meta = {}

    history = get_session_history(session_id)
    return {
        "session_id": session_id,
        "user_message": user_message,
        "assistant_response": output,
        **turn_meta,
        "prior_history_message_count": prior_count,
        "prior_history_snapshot": prior_history_snapshot,
        "history_message_count_after": len(history.messages),
        "history_messages": [
            {"type": message.type, "content": message.content} for message in history.messages
        ],
    }


def run_same_session_demo() -> dict[str, Any]:
    reset_all_sessions()
    session_id = "nykaa-session-demo-a"
    turn1 = run_session_turn(session_id, TURN1_ORDER_QUERY)
    turn2 = run_session_turn(session_id, TURN2_ESCALATION_QUERY)
    return {
        "transcript_id": "A_same_session",
        "session_id": session_id,
        "turn1": turn1,
        "turn2": turn2,
        "session_store_summary": session_store_summary(),
    }


def run_fresh_session_demo() -> dict[str, Any]:
    session_id = "nykaa-session-demo-b"
    turn = run_session_turn(session_id, TURN2_ESCALATION_QUERY)
    return {
        "transcript_id": "B_fresh_session",
        "session_id": session_id,
        "turn": turn,
        "session_store_summary": session_store_summary(),
    }

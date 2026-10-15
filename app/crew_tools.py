"""CrewAI tools for Task 7 — RAG policy lookup and Task 6 order status."""

from __future__ import annotations

import json
from typing import Any

from crewai.tools import tool
from pydantic import BaseModel, Field

from app.grounded_generation import generate_grounded_answer, get_task4_collection
from app.order_status import check_order_status
from app.rag import COLLECTION_FIXED

# Task 5 recommendation — fixed-size chunk collection for production crew RAG.
TASK7_RAG_COLLECTION = COLLECTION_FIXED

RAG_POLICY_CALL_COUNT = 0
RAG_POLICY_TRACE: list[dict[str, Any]] = []

ORDER_STATUS_CALL_COUNT = 0
ORDER_STATUS_TRACE: list[dict[str, Any]] = []


def reset_crew_tool_traces() -> None:
    global RAG_POLICY_CALL_COUNT, ORDER_STATUS_CALL_COUNT
    RAG_POLICY_CALL_COUNT = 0
    ORDER_STATUS_CALL_COUNT = 0
    RAG_POLICY_TRACE.clear()
    ORDER_STATUS_TRACE.clear()


class RagPolicyLookupInput(BaseModel):
    policy_question: str = Field(..., description="Customer policy question to retrieve from the KB.")


class OrderStatusLookupInput(BaseModel):
    record_id: str = Field(..., description="Task 1 ORDERS record_id, e.g. NYK-20261013-0005.")


@tool("rag_policy_lookup")
def rag_policy_lookup(policy_question: str) -> str:
    """Retrieve grounded Nykaa demo policy context from nykaa_fixed_chunks using Task 4 threshold logic."""
    global RAG_POLICY_CALL_COUNT
    RAG_POLICY_CALL_COUNT += 1

    collection = get_task4_collection(collection_name=TASK7_RAG_COLLECTION)
    result = generate_grounded_answer(
        policy_question,
        collection=collection,
    )
    payload = result.to_dict()
    payload["collection_used"] = TASK7_RAG_COLLECTION
    RAG_POLICY_TRACE.append(
        {
            "policy_question": policy_question,
            "payload": payload,
        }
    )
    return json.dumps(payload, sort_keys=True)


@tool("lookup_order_status")
def lookup_order_status(record_id: str) -> str:
    """Look up a real capstone order from dataset.ORDERS via Task 6 check_order_status."""
    global ORDER_STATUS_CALL_COUNT
    ORDER_STATUS_CALL_COUNT += 1

    payload = check_order_status(record_id)
    ORDER_STATUS_TRACE.append({"record_id": record_id, "payload": payload})
    return json.dumps(payload, sort_keys=True)

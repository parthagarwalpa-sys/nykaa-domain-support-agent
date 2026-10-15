"""Build SupportCrewResponse objects from real crew tool traces."""

from __future__ import annotations

from typing import Any

from app import crew_tools
from app.crew_schemas import SupportCrewResponse


def _order_answer(payload: dict[str, Any]) -> str:
    return (
        f"Order {payload['record_id']} is {payload['status']} "
        f"(value {payload['order_value_inr']} INR, escalation_score={payload['escalation_score']})."
    )


def build_support_crew_response_from_traces() -> SupportCrewResponse:
    """Derive structured output only from executed tool traces (not hardcoded demos)."""
    if crew_tools.ORDER_STATUS_TRACE:
        payload = crew_tools.ORDER_STATUS_TRACE[-1]["payload"]
        return SupportCrewResponse(
            answer=_order_answer(payload),
            response_type="order",
            record_id=payload["record_id"],
            status=payload["status"],
            order_value_inr=int(payload["order_value_inr"]),
            escalation_score=float(payload["escalation_score"]),
            sources=[],
            fallback=False,
        )

    if crew_tools.RAG_POLICY_TRACE:
        payload = crew_tools.RAG_POLICY_TRACE[-1]["payload"]
        sources = sorted(
            {chunk["document_id"] for chunk in payload.get("retrieved_chunks", []) if chunk.get("document_id")}
        )
        return SupportCrewResponse(
            answer=str(payload.get("answer") or "").strip(),
            response_type="policy",
            record_id=None,
            status=None,
            order_value_inr=None,
            escalation_score=None,
            sources=sources,
            fallback=bool(payload.get("fallback_fired")),
        )

    return SupportCrewResponse(
        answer="No tool output was available to compose a grounded response.",
        response_type="policy",
        sources=[],
        fallback=True,
    )

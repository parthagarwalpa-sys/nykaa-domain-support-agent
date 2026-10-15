"""Part 3 Task 11 — FastAPI request/response models."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.crew_schemas import SupportCrewResponse


def new_api_session_id() -> str:
    return f"nykaa-api-{uuid.uuid4().hex}"


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Customer support message.")
    session_id: str | None = Field(
        default=None,
        description="Optional session id for LangChain memory; generated when omitted.",
    )


class AskResponse(BaseModel):
    session_id: str
    answer: str
    guardrail_blocked: bool = False
    guardrail_type: str | None = None
    guardrail_reason: str | None = None
    kickoff_used: bool = False
    phone_masks_applied: int = 0
    sanitized_query: str | None = None
    structured: SupportCrewResponse | None = None
    rag_tool_call_count: int | None = None
    order_tool_call_count: int | None = None
    estimated_budget_tokens: int | None = None
    budget_cap_tokens: int | None = None
    governance_outcome: str | None = None


class OrderStatusRequest(BaseModel):
    record_id: str = Field(..., min_length=1)

    @field_validator("record_id")
    @classmethod
    def _nyk_prefix(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("NYK-"):
            raise ValueError("record_id must be a Task 1 ORDERS identifier (NYK- prefix)")
        return cleaned


class OrderStatusResponse(BaseModel):
    record_id: str
    status: str
    order_value_inr: int
    escalation_score: float
    escalation_threshold: float
    escalation_recommended: bool
    days_since_created: int
    delayed_shipment: bool


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "nykaa-support-api"
    mock_llm: bool = True


class WebSocketChatIn(BaseModel):
    query: str = Field(..., min_length=1)


class WebSocketChatOut(BaseModel):
    type: Literal["chat_response"] = "chat_response"
    session_id: str
    answer: str
    guardrail_blocked: bool = False
    guardrail_type: str | None = None
    kickoff_used: bool = False
    structured: SupportCrewResponse | None = None

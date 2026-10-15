"""Part 2 Task 9 — Pydantic schema for validated CrewAI support responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

# Masai brief names this ``response_format``; CrewAI 1.15 maps it to Task ``output_pydantic``.
CREW_RESPONSE_FORMAT_MODEL = "SupportCrewResponse"


class SupportCrewResponse(BaseModel):
    """Structured final response for policy and order support queries."""

    answer: str = Field(min_length=1)
    response_type: Literal["policy", "order"]
    record_id: str | None = None
    status: str | None = None
    order_value_inr: int | None = None
    escalation_score: float | None = Field(default=None, ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)
    fallback: bool = False

    @field_validator("sources")
    @classmethod
    def _sources_use_kb_ids(cls, value: list[str]) -> list[str]:
        for source in value:
            if source and not source.startswith("KB-"):
                raise ValueError(f"Policy source must be a KB document id, got {source!r}")
        return value

    @field_validator("record_id")
    @classmethod
    def _record_id_format(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("NYK-"):
            raise ValueError("record_id must be a Task 1 ORDERS identifier")
        return value


def validate_support_crew_response(payload: object) -> SupportCrewResponse:
    """Validate crew output; raises pydantic ValidationError when invalid."""
    if isinstance(payload, SupportCrewResponse):
        return payload
    if isinstance(payload, BaseModel):
        return SupportCrewResponse.model_validate(payload.model_dump())
    if isinstance(payload, dict):
        return SupportCrewResponse.model_validate(payload)
    if isinstance(payload, str):
        return SupportCrewResponse.model_validate_json(payload)
    raise TypeError(f"Unsupported payload type for SupportCrewResponse: {type(payload)!r}")

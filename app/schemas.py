"""Shared Pydantic models for smoke tests and later pipeline stages."""

from pydantic import BaseModel, Field


class ReviewVerdict(BaseModel):
    """AutoGen Final Editor structured verdict (Masai Task 14 shape)."""

    approved: bool
    final_answer: str
    reason: str = Field(min_length=1)

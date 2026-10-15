"""Step 1B AutoGen smoke entry — delegates to Task 14 production review module."""

from __future__ import annotations

from typing import Any

from app.autogen_review import AutogenReviewInput, run_autogen_review


def run_review_smoke(draft: str, context: str) -> dict[str, Any]:
    review_input = AutogenReviewInput(
        user_query="Step 1B smoke review",
        draft_answer=draft,
        response_type="policy",
        source_document_ids=[],
        policy_context=context,
        order_payload=None,
    )
    return run_autogen_review(review_input)

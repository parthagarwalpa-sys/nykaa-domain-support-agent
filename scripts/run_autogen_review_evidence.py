"""Generate Task 14 AutoGen review evidence under evidence/step15/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.autogen_review import (
    AUTOGEN_MAX_TURNS,
    FINAL_EDITOR_NAME,
    POLICY_COMPLIANCE_REVIEWER_NAME,
    AutogenReviewInput,
    build_autogen_review_team,
    build_review_input_from_crew,
    run_autogen_review,
)
from app.crew_schemas import validate_support_crew_response
from app.support_crew import ORDER_DEMO_RECORD_ID, POLICY_DEMO_QUERY, run_order_demo, run_policy_demo

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step15"


def _json_safe(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _write(name: str, payload: object) -> None:
    path = EVIDENCE_DIR / name
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    _, client, compliance, editor = build_autogen_review_team()
    _write(
        "team_topology.json",
        {
            "team_type": "RoundRobinGroupChat",
            "max_turns": AUTOGEN_MAX_TURNS,
            "agents": [
                {"name": compliance.name, "description": compliance.description},
                {"name": editor.name, "description": editor.description},
                {"output_content_type": "ReviewVerdict"},
            ],
            "custom_message_types": ["StructuredMessage[ReviewVerdict]"],
            "model_client": client.__class__.__name__,
        },
    )

    policy = run_policy_demo()
    structured = validate_support_crew_response(policy["structured_response"])
    approval_input = build_review_input_from_crew(POLICY_DEMO_QUERY, structured, policy)
    approval_outcome = run_autogen_review(approval_input)
    _write("approval_input_package.json", approval_input.__dict__)
    _write(
        "approval_transcript.json",
        {"messages": approval_outcome["messages"], "stop_reason": approval_outcome["stop_reason"]},
    )
    _write("approval_structured_verdict.json", approval_outcome["verdict"])

    kb005_context = (
        "Electronics in this demo catalog include a 12-month limited warranty covering "
        "manufacturing defects under normal use; warranty claims require proof of purchase."
    )
    corrupted_draft = "Electronics have a lifetime warranty on all electronics with unlimited free replacements."
    revision_input = AutogenReviewInput(
        user_query="What warranty applies to Electronics?",
        draft_answer=corrupted_draft,
        response_type="policy",
        source_document_ids=["KB-005"],
        policy_context=kb005_context,
    )
    revision_outcome = run_autogen_review(revision_input)
    _write("revision_input_package.json", revision_input.__dict__)
    _write(
        "revision_transcript.json",
        {"messages": revision_outcome["messages"], "stop_reason": revision_outcome["stop_reason"]},
    )
    _write("revision_structured_verdict.json", revision_outcome["verdict"])

    order = run_order_demo()
    order_structured = validate_support_crew_response(order["structured_response"])
    order_review = build_review_input_from_crew(
        f"Check the status of order {ORDER_DEMO_RECORD_ID}.",
        order_structured,
        order,
    )
    _write("order_review_input_package.json", order_review.__dict__)

    print(f"Wrote Task 14 evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()

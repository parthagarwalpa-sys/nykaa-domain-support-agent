"""Part 2 Task 9 — Pydantic structured CrewAI response tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.crew_schemas import SupportCrewResponse, validate_support_crew_response
from app.order_status import check_order_status
from app.support_crew import (
    ORDER_DEMO_RECORD_ID,
    POLICY_DEMO_QUERY,
    build_support_crew,
    run_order_demo,
    run_policy_demo,
    run_support_crew_kickoff,
)
from app.support_session import run_same_session_demo


def test_support_crew_response_model_exists():
    assert SupportCrewResponse.model_fields["answer"].annotation is str
    assert "response_type" in SupportCrewResponse.model_fields


def test_compose_task_uses_crewai_response_format():
    crew, _, _ = build_support_crew()
    compose_task = crew.tasks[-1]
    assert compose_task.output_pydantic is SupportCrewResponse


def test_policy_query_structured_response_validates():
    outcome = run_policy_demo()
    model = validate_support_crew_response(outcome["structured_response"])
    assert model.response_type == "policy"
    assert model.fallback is False
    assert "KB-001" in model.sources
    assert model.record_id is None
    assert model.status is None


def test_order_query_structured_response_validates():
    expected = check_order_status(ORDER_DEMO_RECORD_ID)
    outcome = run_order_demo()
    model = validate_support_crew_response(outcome["structured_response"])
    assert model.response_type == "order"
    assert model.record_id == ORDER_DEMO_RECORD_ID
    assert model.status == expected["status"]
    assert model.order_value_inr == expected["order_value_inr"]
    assert model.escalation_score == expected["escalation_score"]
    assert model.sources == []


def test_invalid_structured_output_is_rejected():
    with pytest.raises(ValidationError):
        SupportCrewResponse.model_validate(
            {
                "answer": "bad",
                "response_type": "order",
                "record_id": "NOT-A-VALID-ID",
                "sources": [],
                "fallback": False,
            }
        )


def test_kickoff_result_must_validate():
    outcome = run_support_crew_kickoff(POLICY_DEMO_QUERY)
    validated = validate_support_crew_response(outcome["structured_response"])
    assert validated.response_type == "policy"
    assert "structured_response" in outcome


def test_task7_tool_invocation_still_occurs():
    policy = run_policy_demo()
    order = run_order_demo()
    assert policy["rag_tool_call_count"] >= 1
    assert order["order_tool_call_count"] >= 1


def test_task8_memory_still_works():
    demo = run_same_session_demo()
    assert "escalation is recommended" in demo["turn2"]["assistant_response"].lower()


def test_no_external_api_in_structured_modules():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app"
    for name in ("crew_schemas.py", "structured_output.py", "support_crew.py"):
        text = (root / name).read_text(encoding="utf-8").lower()
        assert "openai" not in text
        assert "anthropic" not in text

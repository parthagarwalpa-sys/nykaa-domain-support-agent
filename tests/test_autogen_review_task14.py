"""Part 4 Task 14 — AutoGen independent review stage tests."""

from __future__ import annotations

import inspect

import pytest
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.teams import RoundRobinGroupChat

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
from app.guardrails import run_guarded_support_crew_kickoff
from app.schemas import ReviewVerdict
from app.support_crew import ORDER_DEMO_RECORD_ID, POLICY_DEMO_QUERY, run_policy_demo


def test_team_has_exactly_two_agents():
    team, _, compliance, editor = build_autogen_review_team()
    assert isinstance(team, RoundRobinGroupChat)
    assert len(team._participants) == 2
    assert compliance.name == POLICY_COMPLIANCE_REVIEWER_NAME
    assert editor.name == FINAL_EDITOR_NAME


def test_team_max_turns_is_two():
    team, _, _, _ = build_autogen_review_team()
    assert team._max_turns == 2
    assert AUTOGEN_MAX_TURNS == 2


def test_final_editor_uses_output_content_type():
    _, _, _, final_editor = build_autogen_review_team()
    assert getattr(final_editor, "_output_content_type", None) is ReviewVerdict


def test_team_registers_structured_message_verdict():
    import app.autogen_review as autogen_review_module

    source = inspect.getsource(autogen_review_module.build_autogen_review_team)
    assert "custom_message_types=[StructuredMessage[ReviewVerdict]]" in source
    assert "max_turns=AUTOGEN_MAX_TURNS" in source


def test_actual_autogen_team_execution_occurs():
    outcome = run_autogen_review(
        AutogenReviewInput(
            user_query="smoke",
            draft_answer="Beauty orders may be returned within 15 days if unused.",
            response_type="policy",
            source_document_ids=["KB-001"],
            policy_context="Beauty orders may be returned within 15 days if unused.",
        )
    )
    assert outcome["model_client_calls"] >= 1
    assert outcome["compliance_turns"] >= 1
    assert outcome["editor_turns"] >= 1
    assert outcome["verdict_model"] is not None


def test_grounded_draft_is_approved():
    policy = run_policy_demo()
    structured = validate_support_crew_response(policy["structured_response"])
    review_input = build_review_input_from_crew(POLICY_DEMO_QUERY, structured, policy)
    outcome = run_autogen_review(review_input)
    verdict = outcome["verdict_model"]
    assert isinstance(verdict, ReviewVerdict)
    assert verdict.approved is True


def test_approved_draft_unchanged_exactly():
    draft = structured_answer_from_policy_demo()
    review_input = AutogenReviewInput(
        user_query=POLICY_DEMO_QUERY,
        draft_answer=draft,
        response_type="policy",
        source_document_ids=["KB-001"],
        policy_context=draft,
    )
    verdict = run_autogen_review(review_input)["verdict_model"]
    assert verdict.approved is True
    assert verdict.final_answer == draft


def test_corrupted_draft_not_approved():
    context = (
        "Electronics in this demo catalog include a 12-month limited warranty covering "
        "manufacturing defects under normal use."
    )
    corrupted = "Electronics have a lifetime warranty on all products with unlimited replacements."
    outcome = run_autogen_review(
        AutogenReviewInput(
            user_query="Electronics warranty?",
            draft_answer=corrupted,
            response_type="policy",
            source_document_ids=["KB-005"],
            policy_context=context,
        )
    )
    verdict = outcome["verdict_model"]
    assert verdict.approved is False


def test_corrupted_unsupported_claim_removed_or_revised():
    context = (
        "Electronics in this demo catalog include a 12-month limited warranty covering "
        "manufacturing defects under normal use."
    )
    corrupted = "Electronics have a lifetime warranty on all products with unlimited replacements."
    verdict = run_autogen_review(
        AutogenReviewInput(
            user_query="Electronics warranty?",
            draft_answer=corrupted,
            response_type="policy",
            source_document_ids=["KB-005"],
            policy_context=context,
        )
    )["verdict_model"]
    assert verdict.final_answer != corrupted
    assert "lifetime warranty" not in verdict.final_answer.lower()
    assert "12-month" in verdict.final_answer.lower()


def test_verdict_validates_against_pydantic():
    outcome = run_autogen_review(
        AutogenReviewInput(
            user_query="test",
            draft_answer="Supported line.",
            response_type="policy",
            source_document_ids=[],
            policy_context="Supported line.",
        )
    )
    ReviewVerdict.model_validate(outcome["verdict"])


def test_review_input_includes_retrieved_context():
    policy = run_policy_demo()
    structured = validate_support_crew_response(policy["structured_response"])
    review_input = build_review_input_from_crew(POLICY_DEMO_QUERY, structured, policy)
    assert review_input.policy_context
    assert review_input.source_document_ids


def test_deterministic_mock_llm_client_used():
    _, client, _, _ = build_autogen_review_team()
    assert client.__class__.__name__ == "DeterministicMockChatCompletionClient"


def test_no_external_api_key_required(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    outcome = run_guarded_support_crew_kickoff(POLICY_DEMO_QUERY)
    assert outcome.get("autogen_review") is not None


def test_crewai_flow_still_functional_after_integration():
    outcome = run_guarded_support_crew_kickoff(
        f"Check the status of order {ORDER_DEMO_RECORD_ID}."
    )
    assert outcome["kickoff_used"] is True
    assert outcome["structured_response"]["response_type"] == "order"


def test_task13_evaluation_still_passes():
    from app.evaluation_runner import load_evaluation_queries

    assert len(load_evaluation_queries()) == 15


def structured_answer_from_policy_demo() -> str:
    policy = run_policy_demo()
    return validate_support_crew_response(policy["structured_response"]).answer

"""Part 4 Task 15 — governance (least autonomy, risk, runtime budget)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.crew_tools import reset_crew_tool_traces
from app.governance import (
    AUTHORIZED_ORDER_LOOKUP_AGENT_ROLE,
    BUDGET_ESTIMATION_FORMULA,
    MAX_REQUEST_BUDGET_TOKENS,
    ORDER_LOOKUP_TOOL_NAME,
    REQUEST_BUDGET_EXCEEDED_OUTCOME,
    SYSTEM_RISK_LEVEL,
    SYSTEM_RISK_RATIONALE,
    UnauthorizedAgentCapabilityError,
    agent_capability_matrix,
    assert_least_autonomy_enforced,
    assess_request_budget,
    estimate_request_tokens,
    governance_four_layer_framing,
    resolve_order_lookup_tool_for_role,
)
from app.guardrails import run_guarded_support_crew_kickoff
from app.main import app
from app.memory import reset_all_sessions
from app.request_logging import read_request_log_entries
from app.support_crew import (
    COMPOSER_AGENT_ROLE,
    LOOKUP_AGENT_ROLE,
    POLICY_DEMO_QUERY,
    RETRIEVAL_AGENT_ROLE,
    run_order_demo,
)

OVERSIZED_QUERY = "X" * 5000


@pytest.fixture(autouse=True)
def _reset_traces():
    reset_crew_tool_traces()
    reset_all_sessions()
    yield
    reset_crew_tool_traces()
    reset_all_sessions()


def _tools_for(role: str) -> set[str]:
    for row in agent_capability_matrix():
        if row.agent_role == role:
            return set(row.tool_names)
    raise AssertionError(f"Missing role {role}")


def test_retrieval_agent_has_no_order_lookup_tool():
    tools = _tools_for(RETRIEVAL_AGENT_ROLE)
    assert "rag_policy_lookup" in tools
    assert ORDER_LOOKUP_TOOL_NAME not in tools


def test_composer_agent_has_no_order_lookup_tool():
    tools = _tools_for(COMPOSER_AGENT_ROLE)
    assert ORDER_LOOKUP_TOOL_NAME not in tools
    assert tools == set()


def test_lookup_agent_has_order_lookup_tool():
    tools = _tools_for(LOOKUP_AGENT_ROLE)
    assert ORDER_LOOKUP_TOOL_NAME in tools


def test_unauthorized_agent_capability_rejected():
    with pytest.raises(UnauthorizedAgentCapabilityError):
        resolve_order_lookup_tool_for_role(RETRIEVAL_AGENT_ROLE)


def test_authorized_lookup_agent_resolves_order_tool():
    tool = resolve_order_lookup_tool_for_role(AUTHORIZED_ORDER_LOOKUP_AGENT_ROLE)
    assert getattr(tool, "name", None) == ORDER_LOOKUP_TOOL_NAME


def test_lookup_agent_still_invokes_task6_via_crew():
    outcome = run_order_demo()
    assert outcome["order_tool_call_count"] >= 1


def test_risk_classification_exists():
    assert SYSTEM_RISK_LEVEL in {"Low", "Medium", "High"}


def test_risk_rationale_non_empty():
    assert len(SYSTEM_RISK_RATIONALE) > 80
    assert "Medium" in SYSTEM_RISK_RATIONALE or SYSTEM_RISK_LEVEL == "Medium"


def test_budget_estimator_exists():
    assert BUDGET_ESTIMATION_FORMULA
    assert estimate_request_tokens("abcd") == 1
    assert estimate_request_tokens("a" * 100) == 25


def test_normal_request_within_budget_and_executes():
    assessment = assess_request_budget(POLICY_DEMO_QUERY)
    assert assessment.within_budget is True
    outcome = run_guarded_support_crew_kickoff(POLICY_DEMO_QUERY)
    assert outcome["kickoff_used"] is True


def test_oversized_request_exceeds_budget():
    assessment = assess_request_budget(OVERSIZED_QUERY)
    assert assessment.estimated_tokens > MAX_REQUEST_BUDGET_TOKENS


def test_oversized_request_rejected():
    outcome = run_guarded_support_crew_kickoff(OVERSIZED_QUERY)
    assert outcome["guardrail_blocked"] is True
    assert outcome["governance_outcome"] == REQUEST_BUDGET_EXCEEDED_OUTCOME


def test_oversized_request_skips_crew_kickoff():
    outcome = run_guarded_support_crew_kickoff(OVERSIZED_QUERY)
    assert outcome["kickoff_used"] is False


def test_oversized_request_skips_rag_and_order_tools():
    reset_crew_tool_traces()
    outcome = run_guarded_support_crew_kickoff(OVERSIZED_QUERY)
    assert (outcome.get("rag_tool_call_count") or 0) == 0
    assert (outcome.get("order_tool_call_count") or 0) == 0


def test_oversized_request_skips_autogen_review():
    outcome = run_guarded_support_crew_kickoff(OVERSIZED_QUERY)
    assert outcome.get("autogen_review") is None


def test_budget_rejection_is_pii_safe():
    phone = "9876543210"
    oversized = f"{OVERSIZED_QUERY} {phone}"
    outcome = run_guarded_support_crew_kickoff(oversized)
    assert phone not in str(outcome.get("sanitized_query", ""))


def test_budget_rejection_logs_safe_outcome(tmp_path, monkeypatch: pytest.MonkeyPatch):
    log_path = tmp_path / "requests.jsonl"
    monkeypatch.setenv("NYKAA_REQUEST_LOG_PATH", str(log_path))
    client = TestClient(app)
    response = client.post("/ask", json={"query": OVERSIZED_QUERY})
    assert response.status_code == 200
    entries = read_request_log_entries(log_path)
    assert len(entries) == 1
    assert entries[0]["outcome"] == REQUEST_BUDGET_EXCEEDED_OUTCOME
    assert entries[0].get("estimated_budget_tokens", 0) > MAX_REQUEST_BUDGET_TOKENS
    assert len(entries[0]["request_text"]) < len(OVERSIZED_QUERY)


def test_normal_request_behavior_unchanged():
    outcome = run_guarded_support_crew_kickoff(POLICY_DEMO_QUERY)
    assert outcome["guardrail_blocked"] is False
    assert outcome.get("structured_response") is not None


def test_no_external_api_key_required(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert assert_least_autonomy_enforced() is None


def test_four_layer_framing_documented():
    layers = governance_four_layer_framing()
    assert "application_layer" in layers
    assert "runtime_layer" in layers

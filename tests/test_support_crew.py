"""Part 2 Task 7 — three-agent CrewAI orchestration tests."""

from __future__ import annotations

import json
import os

import pytest

from app import crew_tools
from app.crew_tools import TASK7_RAG_COLLECTION
from app.order_status import check_order_status
from app.rag import COLLECTION_FIXED
from app.support_crew import (
    COMPOSER_AGENT_ROLE,
    LOOKUP_AGENT_ROLE,
    ORDER_DEMO_QUERY,
    ORDER_DEMO_RECORD_ID,
    POLICY_DEMO_QUERY,
    RETRIEVAL_AGENT_ROLE,
    build_support_crew,
    crew_topology,
    ensure_offline_crewai_env,
    run_order_demo,
    run_policy_demo,
    run_support_crew_kickoff,
)


@pytest.fixture(autouse=True)
def _offline_env():
    ensure_offline_crewai_env()


def test_crew_has_three_required_agents():
    _, _, agents = build_support_crew()
    roles = {agent.role for agent in agents}
    assert roles == {RETRIEVAL_AGENT_ROLE, LOOKUP_AGENT_ROLE, COMPOSER_AGENT_ROLE}


def test_agent_tool_assignments():
    topo = crew_topology()
    tools_by_role = {entry["role"]: entry["tools"] for entry in topo["agents"]}
    assert tools_by_role[RETRIEVAL_AGENT_ROLE] == ["rag_policy_lookup"]
    assert tools_by_role[LOOKUP_AGENT_ROLE] == ["lookup_order_status"]
    assert tools_by_role[COMPOSER_AGENT_ROLE] == []


def test_rag_collection_is_task5_fixed_chunks():
    assert TASK7_RAG_COLLECTION == COLLECTION_FIXED == "nykaa_fixed_chunks"


def test_policy_demo_uses_real_kickoff_and_rag_tool():
    outcome = run_policy_demo()
    assert outcome["kickoff_used"] is True
    assert outcome["kickoff_output"]
    assert outcome["rag_tool_call_count"] >= 1
    assert outcome["order_tool_call_count"] == 0
    trace = outcome["rag_tool_trace"][0]["payload"]
    assert trace["collection_used"] == "nykaa_fixed_chunks"
    parent_ids = {chunk["document_id"] for chunk in trace["retrieved_chunks"]}
    assert "KB-001" in parent_ids
    assert trace["answer"]
    assert trace["answer"] in outcome["kickoff_output"] or trace["supporting_context"] in outcome["kickoff_output"]


def test_order_demo_uses_real_kickoff_and_task6_lookup():
    expected = check_order_status(ORDER_DEMO_RECORD_ID)
    outcome = run_order_demo()
    assert outcome["kickoff_used"] is True
    assert outcome["order_tool_call_count"] >= 1
    assert outcome["rag_tool_call_count"] == 0
    payload = outcome["order_tool_trace"][0]["payload"]
    assert payload["status"] == expected["status"]
    assert payload["order_value_inr"] == expected["order_value_inr"]
    assert payload["escalation_score"] == expected["escalation_score"]
    assert str(expected["status"]) in outcome["kickoff_output"]


def test_tool_routing_is_deterministic():
    first = run_support_crew_kickoff(POLICY_DEMO_QUERY)
    second = run_support_crew_kickoff(POLICY_DEMO_QUERY)
    assert first["rag_tool_call_count"] == second["rag_tool_call_count"] == 1
    assert first["order_tool_call_count"] == second["order_tool_call_count"] == 0


def test_support_crew_uses_offline_mock_llm_not_external_api():
    from pathlib import Path

    from app.nykaa_mock_llm import NykaaMockCrewLLM

    _, llm, _ = build_support_crew()
    assert isinstance(llm, NykaaMockCrewLLM)
    bundle = Path(__file__).resolve().parents[1] / "app"
    for rel in ("support_crew.py", "nykaa_mock_llm.py", "crew_tools.py"):
        text = (bundle / rel).read_text(encoding="utf-8").lower()
        for forbidden in ("openai", "anthropic", "groq", "gemini", "litellm"):
            assert forbidden not in text


def test_crewai_telemetry_disabled_before_build():
    ensure_offline_crewai_env()
    assert os.environ.get("CREWAI_DISABLE_TELEMETRY") == "true"
    build_support_crew()


def test_composer_output_reflects_upstream_tool_json():
    outcome = run_order_demo()
    payload_json = json.dumps(outcome["order_tool_trace"][0]["payload"], sort_keys=True)
    assert ORDER_DEMO_RECORD_ID in outcome["kickoff_output"] or payload_json[:40] in outcome["kickoff_output"]


def test_order_tool_does_not_use_smoke_dataset():
    outcome = run_order_demo()
    payload = outcome["order_tool_trace"][0]["payload"]
    assert "proof_token" not in payload
    assert payload["record_id"] == ORDER_DEMO_RECORD_ID

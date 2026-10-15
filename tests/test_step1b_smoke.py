"""Step 1B automated smoke tests: CrewAI BaseLLM tool call + AutoGen structured review."""

from __future__ import annotations

import importlib
import json
import os

import pytest

from app.crew_smoke import run_order_lookup_crew_smoke
from app.mock_autogen_client import DeterministicMockChatCompletionClient
from app.mock_llm import MockCrewLLM
from app.review_smoke import run_review_smoke
from app.schemas import ReviewVerdict
from app import smoke_tools
from app.smoke_tools import reset_order_lookup_trace


def test_mock_crew_llm_instantiates_without_api_keys():
    llm = MockCrewLLM(model="mock-crew-llm")
    assert llm.model == "mock-crew-llm"
    assert os.environ.get("CREWAI_DISABLE_TELEMETRY") == "true"


def test_crewai_kickoff_invokes_order_lookup_tool():
    reset_order_lookup_trace()
    outcome = run_order_lookup_crew_smoke("NYK-SMOKE-001")

    assert outcome["tool_call_count"] >= 1, "Order lookup tool was not invoked"
    trace = outcome["tool_trace"]
    assert trace, "Missing tool execution trace"
    payload = trace[0]["payload"]
    assert payload["proof_token"] == "computed-NYK-SMOKE-001-Shipped"
    assert payload["escalation_score"] == pytest.approx(0.79, abs=0.01)

    assert "computed-NYK-SMOKE-001-Shipped" in outcome["kickoff_output"]
    assert smoke_tools.ORDER_LOOKUP_CALL_COUNT >= 1


def test_autogen_two_agent_review_approves_supported_draft():
    context = (
        "Beauty orders may be returned within 15 days if unused. "
        "Electronics carry a 7-day replacement window for defects."
    )
    draft = "Beauty orders may be returned within 15 days if unused."

    outcome = run_review_smoke(draft, context)
    assert outcome["compliance_turns"] == 1
    assert outcome["editor_turns"] == 1
    assert outcome["model_client_calls"] == 2

    verdict = outcome["verdict_model"]
    assert isinstance(verdict, ReviewVerdict)
    assert verdict.approved is True
    assert verdict.final_answer == draft


def test_autogen_two_agent_review_revises_unsupported_draft():
    context = "Electronics carry a 7-day replacement window for manufacturing defects only."
    draft = (
        "All electronics include a lifetime warranty on all electronics "
        "with unlimited free replacements."
    )

    outcome = run_review_smoke(draft, context)
    assert outcome["compliance_turns"] == 1
    assert outcome["editor_turns"] == 1

    verdict = outcome["verdict_model"]
    assert isinstance(verdict, ReviewVerdict)
    assert verdict.approved is False
    assert verdict.final_answer != draft
    assert "lifetime warranty" not in verdict.final_answer.lower()


def test_offline_modules_do_not_require_api_credentials():
    importlib.import_module("app.mock_llm")
    importlib.import_module("app.mock_autogen_client")
    client = DeterministicMockChatCompletionClient()
    assert client.model_info["function_calling"] is True


def test_import_smoke_for_mandatory_packages():
    import crewai  # noqa: F401
    import autogen_agentchat  # noqa: F401
    import autogen_core  # noqa: F401
    import langchain_core  # noqa: F401
    import sentence_transformers  # noqa: F401
    import chromadb  # noqa: F401
    import fastapi  # noqa: F401
    import pydantic  # noqa: F401

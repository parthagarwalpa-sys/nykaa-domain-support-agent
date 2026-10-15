"""Part 2 Task 8 — LangChain session memory tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from app.memory import (
    get_session_history,
    history_message_count,
    reset_all_sessions,
    session_store_summary,
)
from app.order_status import check_order_status
from app.support_crew import ORDER_DEMO_RECORD_ID, run_order_demo
from app.support_session import (
    MISSING_ORDER_CONTEXT_RESPONSE,
    TURN1_ORDER_QUERY,
    TURN2_ESCALATION_QUERY,
    build_session_chat_runnable,
    run_fresh_session_demo,
    run_same_session_demo,
    run_session_turn,
)


@pytest.fixture(autouse=True)
def _clean_sessions():
    reset_all_sessions()
    yield
    reset_all_sessions()


def test_langchain_history_object_is_used():
    history = get_session_history("unit-session-1")
    assert isinstance(history, InMemoryChatMessageHistory)


def test_runnable_with_message_history_wrapper_is_used():
    runnable = build_session_chat_runnable()
    assert isinstance(runnable, RunnableWithMessageHistory)


def test_first_and_second_turns_are_stored_in_history():
    session_id = "store-session"
    run_session_turn(session_id, TURN1_ORDER_QUERY)
    history = get_session_history(session_id)
    assert len(history.messages) >= 2
    assert history.messages[0].type == "human"
    assert history.messages[1].type == "ai"


def test_second_turn_sees_prior_history_in_same_session():
    session_id = "followup-session"
    run_session_turn(session_id, TURN1_ORDER_QUERY)
    turn2 = run_session_turn(session_id, TURN2_ESCALATION_QUERY)
    assert turn2["prior_history_message_count"] >= 2
    assert TURN1_ORDER_QUERY in turn2["prior_history_snapshot"]
    assert ORDER_DEMO_RECORD_ID in turn2["prior_history_snapshot"]


def test_same_session_escalation_follow_up_uses_prior_order_context():
    demo = run_same_session_demo()
    turn2_response = demo["turn2"]["assistant_response"]
    expected = check_order_status(ORDER_DEMO_RECORD_ID)
    assert ORDER_DEMO_RECORD_ID in turn2_response
    assert str(expected["escalation_score"]) in turn2_response
    assert "escalation is recommended" in turn2_response.lower()


def test_fresh_session_has_no_inherited_order_context():
    run_same_session_demo()
    fresh = run_fresh_session_demo()
    response = fresh["turn"]["assistant_response"]
    assert response == MISSING_ORDER_CONTEXT_RESPONSE
    assert ORDER_DEMO_RECORD_ID not in response
    assert fresh["turn"]["prior_history_message_count"] == 0


def test_two_sessions_remain_isolated():
    run_session_turn("session-alpha", TURN1_ORDER_QUERY)
    fresh_turn = run_session_turn("session-beta", TURN2_ESCALATION_QUERY)
    assert history_message_count("session-alpha") >= 2
    assert history_message_count("session-beta") == 2
    assert fresh_turn["assistant_response"] == MISSING_ORDER_CONTEXT_RESPONSE
    summary = session_store_summary()
    assert "session-alpha" in summary and "session-beta" in summary


def test_session_ids_are_explicit_inputs():
    session_id = "explicit-id-123"
    turn = run_session_turn(session_id, TURN1_ORDER_QUERY)
    assert turn["session_id"] == session_id
    assert session_id in session_store_summary()


def test_memory_module_is_in_process_only():
    source = (Path(__file__).resolve().parents[1] / "app" / "memory.py").read_text(encoding="utf-8").lower()
    for forbidden in ("redis", "sqlalchemy", "supabase", "postgres", "sqlite"):
        assert forbidden not in source


def test_no_external_api_in_memory_modules():
    bundle = Path(__file__).resolve().parents[1] / "app"
    for rel in ("memory.py", "support_session.py"):
        text = (bundle / rel).read_text(encoding="utf-8").lower()
        for forbidden in ("openai", "anthropic", "groq", "gemini"):
            assert forbidden not in text


def test_task7_crew_still_runs():
    outcome = run_order_demo()
    assert outcome["kickoff_used"] is True
    assert outcome["order_tool_call_count"] >= 1

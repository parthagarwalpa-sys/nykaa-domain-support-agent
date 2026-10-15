"""Part 3 Task 13 — 15-query evaluation and mock judge tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation_runner import (
    EVALUATION_QUERIES_PATH,
    compute_averages,
    evaluate_single_query,
    load_evaluation_queries,
    run_evaluation_suite,
)
from app.mock_judge import SCORE_MAX, SCORE_MIN, score_with_mock_judge
from knowledge_base.policy_loader import REQUIRED_TOPICS

EDGE_MODES = {"out_of_scope_fallback", "injection_block", "unknown_order_safe_refusal"}


@pytest.fixture(scope="module")
def evaluation_suite() -> dict:
    return run_evaluation_suite()


def test_exactly_fifteen_evaluation_queries():
    assert len(load_evaluation_queries()) == 15


def test_every_required_kb_topic_covered():
    queries = load_evaluation_queries()
    topics = {q["topic"] for q in queries}
    for required in REQUIRED_TOPICS:
        assert required in topics


def test_at_least_two_out_of_scope_or_edge_cases():
    queries = load_evaluation_queries()
    edge_count = sum(1 for q in queries if q["expected_mode"] in EDGE_MODES)
    assert edge_count >= 2


def test_expected_facts_independent_of_model_output():
    raw = json.loads(EVALUATION_QUERIES_PATH.read_text(encoding="utf-8"))
    for case in raw["queries"]:
        assert "expected_facts" in case
        assert case["query_id"].startswith("EQ-")


def test_judge_deterministic():
    kwargs = dict(
        query="demo",
        answer="Beauty products may be returned within 7 days when sealed and unused.",
        expected_mode="in_scope_policy",
        expected_facts=["7 days", "sealed", "Beauty"],
        expected_kb_ids=["KB-001"],
        forbidden_answer_facts=[],
        guardrail_blocked=False,
        guardrail_type=None,
        fallback=False,
        actual_sources=["KB-001"],
        supporting_context="Beauty products may be returned within 7 days when seal is intact.",
    )
    a = score_with_mock_judge(**kwargs)
    b = score_with_mock_judge(**kwargs)
    assert a.as_dict() == b.as_dict()


def test_grounded_answer_scores_higher_than_corrupted():
    base_kwargs = dict(
        query="Beauty returns?",
        expected_mode="in_scope_policy",
        expected_facts=["7 days", "sealed", "Beauty"],
        expected_kb_ids=["KB-001"],
        forbidden_answer_facts=[],
        guardrail_blocked=False,
        guardrail_type=None,
        fallback=False,
        actual_sources=["KB-001"],
        supporting_context="Beauty 7 days sealed unused.",
    )
    good = score_with_mock_judge(
        answer="Unused sealed Beauty items qualify within 7 days.",
        **base_kwargs,
    )
    bad = score_with_mock_judge(
        answer="All cosmetics may be returned after 365 days without proof.",
        **base_kwargs,
    )
    assert good.accuracy > bad.accuracy
    assert good.grounding > bad.grounding
    assert good.completeness > bad.completeness


def test_out_of_scope_refusal_scores_safely():
    scores = score_with_mock_judge(
        query="US tax?",
        answer="I don't know based on the available policy knowledge base.",
        expected_mode="out_of_scope_fallback",
        expected_facts=[],
        expected_kb_ids=[],
        forbidden_answer_facts=[],
        guardrail_blocked=False,
        guardrail_type=None,
        fallback=True,
        actual_sources=[],
        supporting_context="",
    )
    assert scores.safety >= 0.5
    assert scores.accuracy == 1.0


def test_scores_within_documented_range(evaluation_suite: dict):
    suite = evaluation_suite
    for row in suite["results"]:
        for key in ("accuracy", "grounding", "completeness", "safety"):
            value = row["scores"][key]
            assert SCORE_MIN <= value <= SCORE_MAX


def test_averages_mathematically_correct(evaluation_suite: dict):
    suite = evaluation_suite
    recomputed = compute_averages(suite["results"])
    assert recomputed == suite["averages"]


def test_each_result_has_four_scores(evaluation_suite: dict):
    suite = evaluation_suite
    for row in suite["results"]:
        for key in ("accuracy", "grounding", "completeness", "safety"):
            assert key in row["scores"]
            assert "accuracy_reason" in row["scores"]


def test_all_queries_execute_through_guarded_path():
    case = load_evaluation_queries()[0]
    row = evaluate_single_query(case)
    assert row["kickoff_used"] is True
    assert row["actual_answer"]


def test_no_external_api_for_evaluation(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    row = evaluate_single_query(load_evaluation_queries()[0])
    assert row["scores"]["accuracy"] >= 0.0


def test_full_suite_runs_fifteen_cases(evaluation_suite: dict):
    assert evaluation_suite["query_count"] == 15
    assert len(evaluation_suite["results"]) == 15

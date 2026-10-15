"""Part 1 Task 5 — document-level precision/recall comparison tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.grounded_generation import DEMONSTRATION_IN_SCOPE_QUERIES
from app.rag import COLLECTION_FIXED, COLLECTION_SENTENCE, rebuild_collections
from app.retrieval_evaluation import (
    GROUND_TRUTH_PATH,
    RetrievedChunkRecord,
    aggregate_strategy_metrics,
    compute_confusion,
    dedupe_parent_document_ids,
    evaluate_query_for_strategy,
    load_ground_truth,
    parse_ground_truth_entries,
    recommend_strategy,
    run_full_evaluation,
    safe_ratio,
    validate_evaluation_queries_match_task4,
    StrategyAggregate,
)


def test_ground_truth_is_explicit_and_matches_task4_queries():
    doc = load_ground_truth()
    entries = parse_ground_truth_entries(doc)
    assert len(entries) >= 5
    validate_evaluation_queries_match_task4(entries)
    for entry in entries:
        assert entry.relevant_document_ids
        for doc_id in entry.relevant_document_ids:
            assert doc_id.startswith("KB-")


def test_dedupe_parent_document_ids_counts_each_document_once():
    records = [
        RetrievedChunkRecord("KB-001-fixed-000", "KB-001", 0.1),
        RetrievedChunkRecord("KB-001-fixed-001", "KB-001", 0.2),
        RetrievedChunkRecord("KB-002-fixed-000", "KB-002", 0.3),
    ]
    assert dedupe_parent_document_ids(records) == ["KB-001", "KB-002"]


def test_confusion_and_metric_arithmetic():
    tp, fp, fn, tp_ids, fp_ids, fn_ids = compute_confusion({"KB-001"}, {"KB-001", "KB-005"})
    assert tp == 1 and fp == 1 and fn == 0
    assert tp_ids == {"KB-001"}
    assert fp_ids == {"KB-005"}
    assert fn_ids == set()
    assert safe_ratio(tp, tp + fp) == pytest.approx(0.5)
    assert safe_ratio(tp, tp + fn) == pytest.approx(1.0)


def test_safe_ratio_handles_zero_denominator():
    assert safe_ratio(0, 0) is None


@pytest.fixture(scope="module")
def built_index(tmp_path_factory):
    persist = tmp_path_factory.mktemp("chroma_task5")
    from app.rag import get_embedder

    embedder = get_embedder()
    rebuild_collections(persist_dir=persist, embedder=embedder)
    return {"persist": persist, "embedder": embedder}


def test_both_collections_evaluated_with_same_queries(built_index):
    evaluation = run_full_evaluation(
        persist_dir=built_index["persist"],
        embedder=built_index["embedder"],
    )
    rows = evaluation["per_query_results"]
    assert len(rows) == 10  # 5 queries x 2 strategies

    fixed_queries = {r["query_text"] for r in rows if r["strategy"] == "fixed"}
    sentence_queries = {r["query_text"] for r in rows if r["strategy"] == "sentence"}
    assert fixed_queries == sentence_queries == set(DEMONSTRATION_IN_SCOPE_QUERIES)

    collections = {r["collection"] for r in rows if r["strategy"] == "fixed"}
    assert collections == {COLLECTION_FIXED}
    collections = {r["collection"] for r in rows if r["strategy"] == "sentence"}
    assert collections == {COLLECTION_SENTENCE}


def test_per_query_metrics_match_manual_arithmetic(built_index):
    evaluation = run_full_evaluation(
        persist_dir=built_index["persist"],
        embedder=built_index["embedder"],
    )
    for row in evaluation["per_query_results"]:
        relevant = set(row["relevant_document_ids"])
        retrieved = set(row["retrieved_parent_document_ids"])
        tp = len(relevant & retrieved)
        fp = len(retrieved - relevant)
        fn = len(relevant - retrieved)
        assert row["true_positives"] == tp
        assert row["false_positives"] == fp
        assert row["false_negatives"] == fn
        if tp + fp:
            assert row["precision"] == pytest.approx(tp / (tp + fp))
        if tp + fn:
            assert row["recall"] == pytest.approx(tp / (tp + fn))


def test_aggregate_means_are_correct(built_index):
    evaluation = run_full_evaluation(
        persist_dir=built_index["persist"],
        embedder=built_index["embedder"],
    )
    for strategy in ("fixed", "sentence"):
        rows = [r for r in evaluation["per_query_results"] if r["strategy"] == strategy]
        expected_p = sum(r["precision"] for r in rows) / len(rows)
        expected_r = sum(r["recall"] for r in rows) / len(rows)
        agg = evaluation["aggregates"][strategy]
        assert agg["mean_precision"] == pytest.approx(round(expected_p, 4), rel=1e-3)
        assert agg["mean_recall"] == pytest.approx(round(expected_r, 4), rel=1e-3)


def test_recommendation_uses_measured_aggregates():
    fixed = StrategyAggregate("fixed", COLLECTION_FIXED, 5, 0.7, 1.0, 0.82)
    sentence = StrategyAggregate("sentence", COLLECTION_SENTENCE, 5, 0.6, 1.0, 0.75)
    rec = recommend_strategy(fixed, sentence, fixed_chunk_count=39, sentence_chunk_count=49)
    assert rec["recommended_strategy"] == "fixed"
    assert "0.7000" in rec["rationale_sentences"] or "0.7" in rec["rationale_sentences"]


def test_evaluation_is_deterministic(built_index):
    first = run_full_evaluation(
        persist_dir=built_index["persist"],
        embedder=built_index["embedder"],
    )
    second = run_full_evaluation(
        persist_dir=built_index["persist"],
        embedder=built_index["embedder"],
    )
    assert first["per_query_results"] == second["per_query_results"]
    assert first["aggregates"] == second["aggregates"]


def test_no_external_api_in_evaluation_module():
    source = Path(__file__).resolve().parents[1] / "app" / "retrieval_evaluation.py"
    text = source.read_text(encoding="utf-8").lower()
    for forbidden in ("openai", "anthropic", "groq", "gemini"):
        assert forbidden not in text


def test_evaluate_query_for_strategy_maps_chunk_to_parent(built_index):
    from app.rag import get_chroma_client

    client = get_chroma_client(built_index["persist"])
    collection = client.get_collection(COLLECTION_SENTENCE)
    entries = parse_ground_truth_entries(load_ground_truth())
    metrics = evaluate_query_for_strategy(
        entries[0],
        strategy="sentence",
        collection=collection,
        embedder=built_index["embedder"],
        top_k=3,
    )
    for chunk in metrics.retrieved_chunks:
        assert chunk.document_id.startswith("KB-")
        assert chunk.document_id in chunk.chunk_id

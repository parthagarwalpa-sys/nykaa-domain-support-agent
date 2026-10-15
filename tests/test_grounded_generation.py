"""Part 1 Task 4 — grounded generation, calibration threshold, and MOCK_LLM composer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.grounded_generation import (
    chroma_l2_squared_to_cosine_similarity,
    CALIBRATION_QUERIES,
    DEMONSTRATION_IN_SCOPE_QUERIES,
    DEMONSTRATION_OUT_OF_SCOPE_QUERY,
    EMBEDDING_MODEL_NAME,
    FALLBACK_ANSWER,
    TASK4_COLLECTION_NAME,
    TASK4_TOP_K,
    THRESHOLD_ARTIFACT,
    answer_uses_only_retrieved_context,
    compose_grounded_answer,
    generate_grounded_answer,
    load_retrieval_threshold,
    l2_distance_to_confidence,
    run_demonstration_suite,
    run_threshold_calibration,
    write_threshold_artifact,
)
from app.rag import get_embedder, rebuild_collections


@pytest.fixture(scope="module")
def embedder():
    return get_embedder()


@pytest.fixture(scope="module")
def task4_index(tmp_path_factory, embedder):
    persist = tmp_path_factory.mktemp("chroma_task4")
    rebuild_collections(persist_dir=persist, embedder=embedder)
    threshold_path = persist / "retrieval_threshold.json"
    from app.grounded_generation import get_task4_collection

    collection = get_task4_collection(persist_dir=persist)
    calibration = run_threshold_calibration(collection=collection, embedder=embedder)
    write_threshold_artifact(calibration, path=threshold_path)
    return {
        "persist": persist,
        "embedder": embedder,
        "collection": collection,
        "threshold_path": threshold_path,
        "calibration": calibration,
    }


def test_chroma_index_loads_for_task4(task4_index):
    col = task4_index["collection"]
    assert col.name == TASK4_COLLECTION_NAME
    assert col.count() > 0


def test_query_embedding_uses_task3_model(task4_index):
    from app.rag import EMBEDDING_MODEL_NAME as RAG_MODEL

    embedder = task4_index["embedder"]
    assert RAG_MODEL == EMBEDDING_MODEL_NAME
    assert RAG_MODEL in embedder._model_card_vars.get("model_name", RAG_MODEL)


def test_chroma_l2_squared_to_cosine_formula():
    assert chroma_l2_squared_to_cosine_similarity(0.0) == pytest.approx(1.0)
    assert chroma_l2_squared_to_cosine_similarity(2.0) == pytest.approx(0.0)
    assert chroma_l2_squared_to_cosine_similarity(0.7852) == pytest.approx(0.6074, rel=1e-3)


def test_retrieval_returns_scores_and_parent_metadata(task4_index):
    from app.grounded_generation import retrieve_chunks

    chunks = retrieve_chunks(
        "Beauty return sealed unused",
        collection=task4_index["collection"],
        embedder=task4_index["embedder"],
        top_k=TASK4_TOP_K,
    )
    assert len(chunks) == TASK4_TOP_K
    for chunk in chunks:
        assert chunk.document_id.startswith("KB-")
        assert chunk.l2_distance >= 0.0
        assert chunk.confidence == pytest.approx(l2_distance_to_confidence(chunk.l2_distance))


def test_calibration_has_required_scope_counts(task4_index):
    cal = task4_index["calibration"]
    measurements = cal["calibration_measurements"]
    assert len(measurements) >= 5
    in_scope = [m for m in measurements if m["expected_scope"] == "IN_SCOPE"]
    out_scope = [m for m in measurements if m["expected_scope"] == "OUT_OF_SCOPE"]
    assert len(in_scope) >= 3
    assert len(out_scope) >= 2
    assert len(CALIBRATION_QUERIES) == len(measurements)


def test_threshold_lies_between_observed_clusters(task4_index):
    cal = task4_index["calibration"]
    threshold = cal["selected_threshold"]["max_top1_l2_distance"]
    assert cal["observed_in_scope_top1_l2_max"] < threshold < cal["observed_out_of_scope_top1_l2_min"]


def test_threshold_loaded_from_artifact_not_inline(task4_index):
    loaded = load_retrieval_threshold(task4_index["threshold_path"])
    threshold = loaded["selected_threshold"]["max_top1_l2_distance"]
    assert threshold == task4_index["calibration"]["selected_threshold"]["max_top1_l2_distance"]

    module_source = Path(__file__).resolve().parents[1] / "app" / "grounded_generation.py"
    py_text = module_source.read_text(encoding="utf-8")
    assert str(threshold) not in py_text

    result = generate_grounded_answer(
        DEMONSTRATION_IN_SCOPE_QUERIES[0],
        collection=task4_index["collection"],
        embedder=task4_index["embedder"],
        threshold_path=task4_index["threshold_path"],
    )
    assert result.threshold_max_l2_distance == threshold

    default_doc = load_retrieval_threshold()
    assert default_doc["selected_threshold"]["max_top1_l2_distance"] == threshold


def test_committed_threshold_artifact_exists_and_matches_schema():
    assert THRESHOLD_ARTIFACT.is_file()
    doc = load_retrieval_threshold()
    assert "selected_threshold" in doc
    assert "max_top1_l2_distance" in doc["selected_threshold"]
    assert "calibration_measurements" in doc


def test_in_scope_demonstrations_return_grounded_answers(task4_index):
    for query in DEMONSTRATION_IN_SCOPE_QUERIES:
        result = generate_grounded_answer(
            query,
            collection=task4_index["collection"],
            embedder=task4_index["embedder"],
            threshold_path=task4_index["threshold_path"],
        )
        assert not result.fallback_fired, query
        assert result.answer != FALLBACK_ANSWER
        assert result.retrieved_chunks
        assert answer_uses_only_retrieved_context(result.answer, result.retrieved_chunks)


def test_out_of_scope_demonstration_triggers_threshold_fallback(task4_index):
    result = generate_grounded_answer(
        DEMONSTRATION_OUT_OF_SCOPE_QUERY,
        collection=task4_index["collection"],
        embedder=task4_index["embedder"],
        threshold_path=task4_index["threshold_path"],
    )
    assert result.fallback_fired
    assert result.answer == FALLBACK_ANSWER
    assert result.top1_l2_distance is not None
    assert result.top1_l2_distance > result.threshold_max_l2_distance


def test_compose_is_deterministic(task4_index):
    from app.grounded_generation import retrieve_chunks

    chunks_a = retrieve_chunks(
        DEMONSTRATION_IN_SCOPE_QUERIES[2],
        collection=task4_index["collection"],
        embedder=task4_index["embedder"],
    )
    chunks_b = retrieve_chunks(
        DEMONSTRATION_IN_SCOPE_QUERIES[2],
        collection=task4_index["collection"],
        embedder=task4_index["embedder"],
    )
    assert compose_grounded_answer(chunks_a) == compose_grounded_answer(chunks_b)


def test_demonstration_suite_shape(task4_index):
    rows = run_demonstration_suite(
        collection=task4_index["collection"],
        embedder=task4_index["embedder"],
        threshold_path=task4_index["threshold_path"],
    )
    assert len(rows) == 6
    grounded = [r for r in rows if not r["fallback_fired"]]
    fallbacks = [r for r in rows if r["fallback_fired"]]
    assert len(grounded) == 5
    assert len(fallbacks) == 1


def test_no_external_llm_imports_in_grounded_module():
    import app.grounded_generation as gg

    source = Path(gg.__file__).read_text(encoding="utf-8").lower()
    for forbidden in ("openai", "anthropic", "groq", "gemini", "litellm"):
        assert forbidden not in source

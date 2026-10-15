"""Part 4 Task 16 — in-memory grounded-generation cache tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.grounded_cache import (
    _GROUNDED_CACHE,
    clear_grounded_cache,
    cache_stats,
    make_grounded_cache_key,
    normalize_grounded_query,
)
from app.grounded_generation import (
    DEMONSTRATION_OUT_OF_SCOPE_QUERY,
    FALLBACK_ANSWER,
    generate_grounded_answer,
    get_task4_collection,
)
from app.guardrails import run_guarded_support_crew_kickoff
from app.rag import COLLECTION_FIXED
from app.support_crew import POLICY_DEMO_QUERY

POLICY_QUERY = "What is the return eligibility for Beauty products?"
POLICY_QUERY_VARIANT = "  what   is the return eligibility for beauty products?  "


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_grounded_cache()
    yield
    clear_grounded_cache()


def test_cache_is_in_memory_dict():
    assert isinstance(_GROUNDED_CACHE, dict)


def test_normalization_rules():
    assert normalize_grounded_query(POLICY_QUERY) == normalize_grounded_query(POLICY_QUERY_VARIANT)


def test_cache_key_uses_normalized_query():
    key_a = make_grounded_cache_key(
        normalized_query=normalize_grounded_query(POLICY_QUERY),
        collection_name=COLLECTION_FIXED,
        top_k=3,
    )
    key_b = make_grounded_cache_key(
        normalized_query=normalize_grounded_query(POLICY_QUERY_VARIANT),
        collection_name=COLLECTION_FIXED,
        top_k=3,
    )
    assert key_a == key_b


def test_first_query_is_miss_and_executes_generation():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    before = cache_stats()["grounded_generation_execution_count"]
    generate_grounded_answer(POLICY_QUERY, collection=collection)
    after = cache_stats()
    assert after["cache_misses"] == 1
    assert after["cache_hits"] == 0
    assert after["grounded_generation_execution_count"] == before + 1


def test_result_stored_after_miss():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    generate_grounded_answer(POLICY_QUERY, collection=collection)
    assert cache_stats()["entries"] == 1


def test_second_identical_query_is_hit():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    generate_grounded_answer(POLICY_QUERY, collection=collection)
    exec_after_first = cache_stats()["grounded_generation_execution_count"]
    generate_grounded_answer(POLICY_QUERY, collection=collection)
    stats = cache_stats()
    assert stats["cache_hits"] == 1
    assert stats["grounded_generation_execution_count"] == exec_after_first


def test_hit_returns_identical_grounded_result():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    first = generate_grounded_answer(POLICY_QUERY, collection=collection)
    second = generate_grounded_answer(POLICY_QUERY, collection=collection)
    assert first.answer == second.answer
    assert first.to_dict() == second.to_dict()


def test_equivalent_whitespace_case_query_hits_same_entry():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    generate_grounded_answer(POLICY_QUERY, collection=collection)
    exec_count = cache_stats()["grounded_generation_execution_count"]
    generate_grounded_answer(POLICY_QUERY_VARIANT, collection=collection)
    assert cache_stats()["cache_hits"] == 1
    assert cache_stats()["grounded_generation_execution_count"] == exec_count


def test_unrelated_query_different_cache_entry():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    generate_grounded_answer(POLICY_QUERY, collection=collection)
    generate_grounded_answer("How many payment retries are allowed at checkout?", collection=collection)
    assert cache_stats()["entries"] == 2
    assert cache_stats()["grounded_generation_execution_count"] == 2


def test_clear_cache_resets_counters_and_entries():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    generate_grounded_answer(POLICY_QUERY, collection=collection)
    clear_grounded_cache()
    stats = cache_stats()
    assert stats["entries"] == 0
    assert stats["cache_hits"] == 0
    assert stats["grounded_generation_execution_count"] == 0


def test_fallback_results_can_be_cached():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    first = generate_grounded_answer(DEMONSTRATION_OUT_OF_SCOPE_QUERY, collection=collection)
    second = generate_grounded_answer(DEMONSTRATION_OUT_OF_SCOPE_QUERY, collection=collection)
    assert first.fallback_fired is True
    assert second.fallback_fired is True
    assert second.answer == FALLBACK_ANSWER
    assert cache_stats()["cache_hits"] == 1


def test_guardrails_still_functional_with_cache():
    clear_grounded_cache()
    outcome = run_guarded_support_crew_kickoff(POLICY_DEMO_QUERY)
    assert outcome["kickoff_used"] is True


def test_autogen_still_runs_downstream():
    clear_grounded_cache()
    outcome = run_guarded_support_crew_kickoff(POLICY_DEMO_QUERY)
    assert outcome.get("autogen_review") is not None


def test_no_external_cache_service():
    import app.grounded_cache as gc_mod

    source = Path(gc_mod.__file__).read_text(encoding="utf-8").lower()
    assert "redis" not in source
    assert "memcached" not in source


def test_behavior_is_deterministic():
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)
    clear_grounded_cache()
    a = generate_grounded_answer(POLICY_QUERY, collection=collection)
    clear_grounded_cache()
    b = generate_grounded_answer(POLICY_QUERY, collection=collection)
    assert a.answer == b.answer

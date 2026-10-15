"""Generate Task 16 cache evidence under evidence/step17/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.grounded_cache import (
    clear_grounded_cache,
    cache_stats,
    make_grounded_cache_key,
    normalize_grounded_query,
)
from app.grounded_generation import generate_grounded_answer, get_task4_collection
from app.rag import COLLECTION_FIXED

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step17"
QUERY = "What is the return eligibility for Beauty products?"
QUERY_VARIANT = "  what   is the return eligibility for beauty products?  "


def _write(name: str, payload: object) -> None:
    path = EVIDENCE_DIR / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    clear_grounded_cache()
    collection = get_task4_collection(collection_name=COLLECTION_FIXED)

    _write(
        "cache_configuration.json",
        {
            "scope": "Task 4 generate_grounded_answer only",
            "storage": "in-memory dict (process local)",
            "collection": COLLECTION_FIXED,
            "top_k": 3,
        },
    )
    _write(
        "normalization_examples.json",
        {
            "raw_a": QUERY,
            "raw_b": QUERY_VARIANT,
            "normalized_a": normalize_grounded_query(QUERY),
            "normalized_b": normalize_grounded_query(QUERY_VARIANT),
            "cache_key": make_grounded_cache_key(
                normalized_query=normalize_grounded_query(QUERY),
                collection_name=COLLECTION_FIXED,
                top_k=3,
            ),
            "punctuation_note": "Punctuation is not altered; only case and whitespace collapse.",
        },
    )

    stats_before = cache_stats()
    first = generate_grounded_answer(QUERY, collection=collection)
    stats_after_first = cache_stats()
    _write(
        "first_request_cache_miss.json",
        {
            "cache_hit": False,
            "stats_before": stats_before,
            "stats_after": stats_after_first,
            "answer_preview": first.answer[:200],
            "fallback_fired": first.fallback_fired,
        },
    )

    stats_before_second = cache_stats()
    second = generate_grounded_answer(QUERY, collection=collection)
    stats_after_second = cache_stats()
    _write(
        "second_request_cache_hit.json",
        {
            "cache_hit": True,
            "stats_before": stats_before_second,
            "stats_after": stats_after_second,
            "grounded_generation_execution_count_unchanged": (
                stats_before_second["grounded_generation_execution_count"]
                == stats_after_second["grounded_generation_execution_count"]
            ),
            "answer_preview": second.answer[:200],
        },
    )

    _write(
        "call_counter_before_after.json",
        {
            "executions_after_first_call": stats_after_first["grounded_generation_execution_count"],
            "executions_after_second_call": stats_after_second["grounded_generation_execution_count"],
            "cache_hits_after_second": stats_after_second["cache_hits"],
        },
    )

    _write(
        "identical_result_proof.json",
        {
            "first_answer": first.answer,
            "second_answer": second.answer,
            "identical": first.to_dict() == second.to_dict(),
        },
    )

    clear_grounded_cache()
    generate_grounded_answer(QUERY, collection=collection)
    variant = generate_grounded_answer(QUERY_VARIANT, collection=collection)
    _write(
        "equivalent_normalized_query_hit.json",
        {
            "cache_hits": cache_stats()["cache_hits"],
            "executions": cache_stats()["grounded_generation_execution_count"],
            "variant_answer_matches": variant.answer == first.answer,
        },
    )

    print(f"Wrote Task 16 evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()

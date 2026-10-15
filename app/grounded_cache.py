"""Part 4 Task 16 — in-memory cache for Task 4 grounded generation."""

from __future__ import annotations

import re
from typing import Any

from app.grounded_generation import GroundedGenerationResult, RetrievedChunk

# In-process only; cleared on process restart.
_GROUNDED_CACHE: dict[str, dict[str, Any]] = {}

CACHE_HITS = 0
CACHE_MISSES = 0
GROUNDED_GENERATION_EXECUTION_COUNT = 0


def normalize_grounded_query(text: str) -> str:
    """Deterministic exact-match key: trim, collapse whitespace, lowercase."""
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed.lower()


def make_grounded_cache_key(*, normalized_query: str, collection_name: str, top_k: int) -> str:
    return f"{collection_name}|k={top_k}|{normalized_query}"


def clear_grounded_cache() -> None:
    global CACHE_HITS, CACHE_MISSES, GROUNDED_GENERATION_EXECUTION_COUNT
    _GROUNDED_CACHE.clear()
    CACHE_HITS = 0
    CACHE_MISSES = 0
    GROUNDED_GENERATION_EXECUTION_COUNT = 0


def cache_stats() -> dict[str, int]:
    return {
        "entries": len(_GROUNDED_CACHE),
        "cache_hits": CACHE_HITS,
        "cache_misses": CACHE_MISSES,
        "grounded_generation_execution_count": GROUNDED_GENERATION_EXECUTION_COUNT,
    }


def grounded_result_from_payload(payload: dict[str, Any]) -> GroundedGenerationResult:
    chunks = [
        RetrievedChunk(
            chunk_id=c["chunk_id"],
            document_id=c["document_id"],
            title=c["title"],
            topic=c["topic"],
            source_file=c["source_file"],
            text=c["text"],
            l2_distance=float(c["l2_distance"]),
            confidence=float(c["confidence"]),
        )
        for c in payload.get("retrieved_chunks", [])
    ]
    return GroundedGenerationResult(
        query=str(payload["query"]),
        collection=str(payload["collection"]),
        top_k=int(payload["top_k"]),
        threshold_max_l2_distance=float(payload["threshold_max_l2_distance"]),
        threshold_rationale=str(payload["threshold_rationale"]),
        fallback_fired=bool(payload["fallback_fired"]),
        top1_l2_distance=payload.get("top1_l2_distance"),
        top1_confidence=payload.get("top1_confidence"),
        retrieved_chunks=chunks,
        supporting_context=str(payload.get("supporting_context") or ""),
        answer=str(payload.get("answer") or ""),
    )


def try_get_cached_grounded(key: str) -> tuple[bool, GroundedGenerationResult | None]:
    global CACHE_HITS
    payload = _GROUNDED_CACHE.get(key)
    if payload is None:
        return False, None
    CACHE_HITS += 1
    return True, grounded_result_from_payload(payload)


def store_grounded_cache(key: str, result: GroundedGenerationResult) -> None:
    _GROUNDED_CACHE[key] = result.to_dict()


def record_cache_miss() -> None:
    global CACHE_MISSES
    CACHE_MISSES += 1


def record_grounded_generation_execution() -> None:
    global GROUNDED_GENERATION_EXECUTION_COUNT
    GROUNDED_GENERATION_EXECUTION_COUNT += 1

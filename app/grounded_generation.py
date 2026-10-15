"""Part 1 Task 4 — grounded policy answers with empirically calibrated retrieval fallback."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from app.rag import (
    COLLECTION_SENTENCE,
    DEFAULT_CHROMA_DIR,
    EMBEDDING_MODEL_NAME,
    get_chroma_client,
    get_embedder,
    query_collection,
)

# Provisional Task 4 collection — formal comparison is Task 5, not a deployment recommendation.
TASK4_COLLECTION_NAME = COLLECTION_SENTENCE
TASK4_TOP_K = 3

FALLBACK_ANSWER = "I don't know based on the available policy knowledge base."

THRESHOLD_ARTIFACT = Path(__file__).resolve().parent / "data" / "retrieval_threshold.json"

ScopeLabel = Literal["IN_SCOPE", "OUT_OF_SCOPE"]

# Chroma default metric is ``l2``: Euclidean distance *squared* (see Chroma distance docs).
# Task 3 uses normalize_embeddings=True, so for unit vectors:
#   raw_l2_squared = 2 - 2 * cosine_similarity  =>  cosine_similarity = 1 - raw_l2_squared / 2
CHROMA_SCORE_FIELD = "distances"
CHROMA_DISTANCE_METRIC = "l2"
CHROMA_DISTANCE_SEMANTICS = "squared_euclidean (Chroma default l2)"
CONFIDENCE_FROM_CHROMA_L2_FORMULA = "cosine_similarity = 1 - raw_chroma_l2_squared / 2  (unit-normalized embeddings)"


@dataclass(frozen=True)
class CalibrationQuery:
    query: str
    scope: ScopeLabel
    topic: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    topic: str
    source_file: str
    text: str
    l2_distance: float
    confidence: float


@dataclass(frozen=True)
class GroundedGenerationResult:
    query: str
    collection: str
    top_k: int
    threshold_max_l2_distance: float
    threshold_rationale: str
    fallback_fired: bool
    top1_l2_distance: float | None
    top1_confidence: float | None
    retrieved_chunks: list[RetrievedChunk]
    supporting_context: str
    answer: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["retrieved_chunks"] = [asdict(c) for c in self.retrieved_chunks]
        return payload


# Dedicated calibration set (>=3 in-scope, >=2 out-of-scope).
CALIBRATION_QUERIES: tuple[CalibrationQuery, ...] = (
    CalibrationQuery(
        query="Can I return an unused sealed Beauty product within seven days?",
        scope="IN_SCOPE",
        topic="Beauty product returns",
    ),
    CalibrationQuery(
        query="How long does a Cash on Delivery refund take to reach my bank account?",
        scope="IN_SCOPE",
        topic="COD refunds",
    ),
    CalibrationQuery(
        query="Can I cancel my order if it is still in Placed status within the first hour?",
        scope="IN_SCOPE",
        topic="Order cancellation",
    ),
    CalibrationQuery(
        query="What is the weather forecast in Mumbai tomorrow?",
        scope="OUT_OF_SCOPE",
        topic="Weather (unrelated)",
    ),
    CalibrationQuery(
        query="What are the roots of the quadratic equation x squared minus five x plus six?",
        scope="OUT_OF_SCOPE",
        topic="Mathematics (unrelated)",
    ),
)

# Five in-scope demonstration queries (distinct policy topics).
DEMONSTRATION_IN_SCOPE_QUERIES: tuple[str, ...] = (
    "What is the return eligibility for unused sealed Beauty products?",
    "What is the timeline for COD refunds to a bank account?",
    "What is the express delivery SLA for metro tier-1 cities?",
    "What is the cancellation policy for orders still in Placed status?",
    "How does size exchange work for Apparel and Footwear?",
)

DEMONSTRATION_OUT_OF_SCOPE_QUERY = (
    "How do I file US federal income tax as a nonresident alien?"
)


def chroma_l2_squared_to_cosine_similarity(raw_l2_squared: float) -> float:
    """Map Chroma ``l2`` score (squared Euclidean) to cosine similarity for unit vectors."""
    return 1.0 - raw_l2_squared / 2.0


def l2_distance_to_confidence(l2_distance: float) -> float:
    """Alias: ``l2_distance`` fields store Chroma's raw squared-L2 distance."""
    return chroma_l2_squared_to_cosine_similarity(l2_distance)


def load_retrieval_threshold(path: Path | None = None) -> dict[str, Any]:
    artifact = path or THRESHOLD_ARTIFACT
    with artifact.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_task4_collection(
    persist_dir: Path | str = DEFAULT_CHROMA_DIR,
    collection_name: str = TASK4_COLLECTION_NAME,
) -> Collection:
    client = get_chroma_client(persist_dir)
    return client.get_collection(collection_name)


def _parse_retrieval_rows(
    raw: dict[str, Any],
) -> list[RetrievedChunk]:
    ids = raw["ids"][0]
    documents = raw["documents"][0]
    metadatas = raw["metadatas"][0]
    distances = raw["distances"][0]
    chunks: list[RetrievedChunk] = []
    for chunk_id, text, meta, dist in zip(ids, documents, metadatas, distances, strict=True):
        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                document_id=meta["document_id"],
                title=meta["title"],
                topic=meta["topic"],
                source_file=meta["source_file"],
                text=text,
                l2_distance=float(dist),
                confidence=l2_distance_to_confidence(float(dist)),
            )
        )
    return chunks


def retrieve_chunks(
    query: str,
    *,
    collection: Collection,
    embedder: SentenceTransformer,
    top_k: int = TASK4_TOP_K,
) -> list[RetrievedChunk]:
    raw = query_collection(collection, query, embedder, n_results=top_k)
    return _parse_retrieval_rows(raw)


def select_supporting_context(chunks: list[RetrievedChunk]) -> str:
    """Deterministic supporting context: deduplicated retrieved chunk text in rank order."""
    seen: set[str] = set()
    parts: list[str] = []
    for chunk in chunks:
        normalized = chunk.text.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            parts.append(normalized)
    return " ".join(parts)


def compose_grounded_answer(chunks: list[RetrievedChunk]) -> str:
    """MOCK_LLM deterministic composer — no external LLM; text comes only from retrieval."""
    if not chunks:
        return FALLBACK_ANSWER
    context = select_supporting_context(chunks)
    lead = chunks[0]
    return f"According to {lead.title} ({lead.document_id}): {context}"


def should_fallback(top1_l2_distance: float, max_l2_distance: float) -> bool:
    return top1_l2_distance > max_l2_distance


def _generate_grounded_answer_uncached(
    query: str,
    *,
    collection: Collection,
    embedder: SentenceTransformer,
    top_k: int,
    threshold_path: Path | None,
) -> GroundedGenerationResult:
    threshold_doc = load_retrieval_threshold(threshold_path)
    max_l2 = float(threshold_doc["selected_threshold"]["max_top1_l2_distance"])
    rationale = str(threshold_doc["selected_threshold"]["rationale"])

    chunks = retrieve_chunks(query, collection=collection, embedder=embedder, top_k=top_k)
    if not chunks:
        return GroundedGenerationResult(
            query=query,
            collection=collection.name,
            top_k=top_k,
            threshold_max_l2_distance=max_l2,
            threshold_rationale=rationale,
            fallback_fired=True,
            top1_l2_distance=None,
            top1_confidence=None,
            retrieved_chunks=[],
            supporting_context="",
            answer=FALLBACK_ANSWER,
        )

    top1 = chunks[0]
    fallback = should_fallback(top1.l2_distance, max_l2)
    supporting = "" if fallback else select_supporting_context(chunks)
    answer = FALLBACK_ANSWER if fallback else compose_grounded_answer(chunks)

    return GroundedGenerationResult(
        query=query,
        collection=collection.name,
        top_k=top_k,
        threshold_max_l2_distance=max_l2,
        threshold_rationale=rationale,
        fallback_fired=fallback,
        top1_l2_distance=top1.l2_distance,
        top1_confidence=top1.confidence,
        retrieved_chunks=chunks,
        supporting_context=supporting,
        answer=answer,
    )


def generate_grounded_answer(
    query: str,
    *,
    collection: Collection | None = None,
    embedder: SentenceTransformer | None = None,
    top_k: int = TASK4_TOP_K,
    threshold_path: Path | None = None,
    persist_dir: Path | str = DEFAULT_CHROMA_DIR,
) -> GroundedGenerationResult:
    from app.grounded_cache import (
        make_grounded_cache_key,
        normalize_grounded_query,
        record_cache_miss,
        record_grounded_generation_execution,
        store_grounded_cache,
        try_get_cached_grounded,
    )

    model = embedder or get_embedder()
    col = collection or get_task4_collection(persist_dir=persist_dir)
    cache_key = make_grounded_cache_key(
        normalized_query=normalize_grounded_query(query),
        collection_name=col.name,
        top_k=top_k,
    )
    hit, cached = try_get_cached_grounded(cache_key)
    if hit and cached is not None:
        return cached

    record_cache_miss()
    record_grounded_generation_execution()
    result = _generate_grounded_answer_uncached(
        query,
        collection=col,
        embedder=model,
        top_k=top_k,
        threshold_path=threshold_path,
    )
    store_grounded_cache(cache_key, result)
    return result


def _round4(value: float) -> float:
    return round(value, 4)


def run_threshold_calibration(
    *,
    collection: Collection,
    embedder: SentenceTransformer,
    calibration_queries: tuple[CalibrationQuery, ...] = CALIBRATION_QUERIES,
) -> dict[str, Any]:
    measurements: list[dict[str, Any]] = []
    in_scope_distances: list[float] = []
    out_scope_distances: list[float] = []

    for item in calibration_queries:
        chunks = retrieve_chunks(item.query, collection=collection, embedder=embedder, top_k=1)
        top = chunks[0]
        measurements.append(
            {
                "query": item.query,
                "expected_scope": item.scope,
                "topic": item.topic,
                "top1_chunk_id": top.chunk_id,
                "top1_parent_document_id": top.document_id,
                "top1_title": top.title,
                "raw_chroma_l2_distance": _round4(top.l2_distance),
                "interpreted_confidence_cosine_similarity": _round4(top.confidence),
            }
        )
        if item.scope == "IN_SCOPE":
            in_scope_distances.append(top.l2_distance)
        else:
            out_scope_distances.append(top.l2_distance)

    max_in = max(in_scope_distances)
    min_out = min(out_scope_distances)

    if max_in >= min_out:
        raise ValueError(
            "Calibration clusters overlap: "
            f"max in-scope top-1 L2={max_in:.4f}, min out-of-scope top-1 L2={min_out:.4f}. "
            "Refine calibration queries or inspect retrieval."
        )

    # Midpoint strictly between observed in-scope and out-of-scope top-1 L2 distances.
    threshold_distance = (max_in + min_out) / 2.0
    rationale = (
        f"Observed in-scope top-1 L2 distances up to {_round4(max_in)}; "
        f"out-of-scope top-1 L2 distances from {_round4(min_out)} upward. "
        f"Selected max_top1_l2_distance={_round4(threshold_distance)} as the midpoint "
        f"between the two clusters ({CHROMA_DISTANCE_METRIC} on {EMBEDDING_MODEL_NAME} "
        f"with normalize_embeddings=True). Cosine interpretation: {CONFIDENCE_FROM_CHROMA_L2_FORMULA}."
    )

    return {
        "task4_collection_provisional": collection.name,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "chroma_score_field": CHROMA_SCORE_FIELD,
        "chroma_distance_metric": CHROMA_DISTANCE_METRIC,
        "chroma_distance_semantics": CHROMA_DISTANCE_SEMANTICS,
        "confidence_interpretation": CONFIDENCE_FROM_CHROMA_L2_FORMULA,
        "calibration_measurements": measurements,
        "observed_in_scope_top1_l2_max": _round4(max_in),
        "observed_out_of_scope_top1_l2_min": _round4(min_out),
        "selected_threshold": {
            "max_top1_l2_distance": _round4(threshold_distance),
            "rationale": rationale,
        },
    }


def write_threshold_artifact(calibration: dict[str, Any], path: Path | None = None) -> Path:
    target = path or THRESHOLD_ARTIFACT
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(calibration, handle, indent=2)
        handle.write("\n")
    return target


def answer_uses_only_retrieved_context(answer: str, chunks: list[RetrievedChunk]) -> bool:
    """Verify MOCK_LLM answer matches deterministic composition from retrieved chunks only."""
    if answer == FALLBACK_ANSWER:
        return True
    expected = compose_grounded_answer(chunks)
    return answer == expected


def run_demonstration_suite(
    *,
    collection: Collection,
    embedder: SentenceTransformer,
    threshold_path: Path | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for query in DEMONSTRATION_IN_SCOPE_QUERIES:
        outcome = generate_grounded_answer(
            query,
            collection=collection,
            embedder=embedder,
            threshold_path=threshold_path,
        )
        results.append(outcome.to_dict())
    out_scope = generate_grounded_answer(
        DEMONSTRATION_OUT_OF_SCOPE_QUERY,
        collection=collection,
        embedder=embedder,
        threshold_path=threshold_path,
    )
    results.append(out_scope.to_dict())
    return results

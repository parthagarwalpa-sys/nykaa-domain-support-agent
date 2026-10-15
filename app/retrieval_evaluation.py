"""Part 1 Task 5 — document-level precision/recall for both chunking collections."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from app.grounded_generation import DEMONSTRATION_IN_SCOPE_QUERIES, TASK4_TOP_K
from app.rag import (
    COLLECTION_FIXED,
    COLLECTION_SENTENCE,
    DEFAULT_CHROMA_DIR,
    EMBEDDING_MODEL_NAME,
    get_chroma_client,
    get_embedder,
    query_collection,
)

GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "data" / "retrieval_ground_truth.json"

StrategyName = Literal["fixed", "sentence"]
STRATEGY_TO_COLLECTION: dict[StrategyName, str] = {
    "fixed": COLLECTION_FIXED,
    "sentence": COLLECTION_SENTENCE,
}


@dataclass(frozen=True)
class GroundTruthEntry:
    query_id: str
    topic: str
    query_text: str
    relevant_document_ids: tuple[str, ...]
    relevance_rationale: str


@dataclass(frozen=True)
class RetrievedChunkRecord:
    chunk_id: str
    document_id: str
    raw_chroma_l2_squared: float


@dataclass(frozen=True)
class QueryStrategyMetrics:
    query_id: str
    query_text: str
    topic: str
    collection: str
    strategy: StrategyName
    top_k: int
    relevant_document_ids: tuple[str, ...]
    retrieved_chunks: tuple[RetrievedChunkRecord, ...]
    retrieved_parent_document_ids: tuple[str, ...]
    true_positives: int
    false_positives: int
    false_negatives: int
    true_positive_ids: tuple[str, ...]
    false_positive_ids: tuple[str, ...]
    false_negative_ids: tuple[str, ...]
    precision: float | None
    recall: float | None
    precision_expression: str
    recall_expression: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyAggregate:
    strategy: StrategyName
    collection: str
    query_count: int
    mean_precision: float
    mean_recall: float
    mean_f1: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_ground_truth(path: Path | None = None) -> dict[str, Any]:
    artifact = path or GROUND_TRUTH_PATH
    with artifact.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_ground_truth_entries(doc: dict[str, Any]) -> list[GroundTruthEntry]:
    entries: list[GroundTruthEntry] = []
    for row in doc["entries"]:
        entries.append(
            GroundTruthEntry(
                query_id=row["query_id"],
                topic=row["topic"],
                query_text=row["query_text"],
                relevant_document_ids=tuple(row["relevant_document_ids"]),
                relevance_rationale=row["relevance_rationale"],
            )
        )
    return entries


def validate_evaluation_queries_match_task4(entries: list[GroundTruthEntry]) -> None:
    gt_queries = [entry.query_text for entry in entries]
    task4_queries = list(DEMONSTRATION_IN_SCOPE_QUERIES)
    if gt_queries != task4_queries:
        raise ValueError(
            "Ground-truth query_text list must match Task 4 DEMONSTRATION_IN_SCOPE_QUERIES exactly."
        )


def dedupe_parent_document_ids(chunk_records: list[RetrievedChunkRecord]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for record in chunk_records:
        if record.document_id not in seen:
            seen.add(record.document_id)
            ordered.append(record.document_id)
    return ordered


def compute_confusion(
    relevant_ids: set[str],
    retrieved_parent_ids: set[str],
) -> tuple[int, int, int, set[str], set[str], set[str]]:
    tp_ids = relevant_ids & retrieved_parent_ids
    fp_ids = retrieved_parent_ids - relevant_ids
    fn_ids = relevant_ids - retrieved_parent_ids
    return len(tp_ids), len(fp_ids), len(fn_ids), tp_ids, fp_ids, fn_ids


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def format_precision_expression(tp: int, fp: int, precision: float | None) -> str:
    denom = tp + fp
    if denom == 0:
        return f"TP={tp}, FP={fp}; precision undefined (TP+FP=0)"
    value = "undefined" if precision is None else f"{precision:.4f}"
    return f"precision = TP / (TP + FP) = {tp} / ({tp} + {fp}) = {tp}/{denom} = {value}"


def format_recall_expression(tp: int, fn: int, recall: float | None) -> str:
    denom = tp + fn
    if denom == 0:
        return f"TP={tp}, FN={fn}; recall undefined (TP+FN=0)"
    value = "undefined" if recall is None else f"{recall:.4f}"
    return f"recall = TP / (TP + FN) = {tp} / ({tp} + {fn}) = {tp}/{denom} = {value}"


def retrieve_chunk_records(
    collection: Collection,
    query_text: str,
    embedder: SentenceTransformer,
    top_k: int,
) -> list[RetrievedChunkRecord]:
    raw = query_collection(collection, query_text, embedder, n_results=top_k)
    ids = raw["ids"][0]
    metadatas = raw["metadatas"][0]
    distances = raw["distances"][0]
    records: list[RetrievedChunkRecord] = []
    for chunk_id, meta, dist in zip(ids, metadatas, distances, strict=True):
        records.append(
            RetrievedChunkRecord(
                chunk_id=chunk_id,
                document_id=meta["document_id"],
                raw_chroma_l2_squared=float(dist),
            )
        )
    return records


def evaluate_query_for_strategy(
    entry: GroundTruthEntry,
    *,
    strategy: StrategyName,
    collection: Collection,
    embedder: SentenceTransformer,
    top_k: int,
) -> QueryStrategyMetrics:
    chunks = retrieve_chunk_records(collection, entry.query_text, embedder, top_k)
    parent_ids = dedupe_parent_document_ids(chunks)
    relevant_set = set(entry.relevant_document_ids)
    retrieved_set = set(parent_ids)
    tp, fp, fn, tp_ids, fp_ids, fn_ids = compute_confusion(relevant_set, retrieved_set)
    precision = safe_ratio(tp, tp + fp)
    recall = safe_ratio(tp, tp + fn)

    return QueryStrategyMetrics(
        query_id=entry.query_id,
        query_text=entry.query_text,
        topic=entry.topic,
        collection=collection.name,
        strategy=strategy,
        top_k=top_k,
        relevant_document_ids=entry.relevant_document_ids,
        retrieved_chunks=tuple(chunks),
        retrieved_parent_document_ids=tuple(parent_ids),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_positive_ids=tuple(sorted(tp_ids)),
        false_positive_ids=tuple(sorted(fp_ids)),
        false_negative_ids=tuple(sorted(fn_ids)),
        precision=precision,
        recall=recall,
        precision_expression=format_precision_expression(tp, fp, precision),
        recall_expression=format_recall_expression(tp, fn, recall),
    )


def mean_metric(values: list[float | None]) -> float:
    usable = [value for value in values if value is not None]
    if not usable:
        return 0.0
    return sum(usable) / len(usable)


def f1_score(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def aggregate_strategy_metrics(rows: list[QueryStrategyMetrics]) -> StrategyAggregate:
    strategy = rows[0].strategy
    collection = rows[0].collection
    precisions = [row.precision for row in rows]
    recalls = [row.recall for row in rows]
    mean_p = mean_metric(precisions)
    mean_r = mean_metric(recalls)
    f1_values = [f1_score(p, r) for p, r in zip(precisions, recalls, strict=True)]
    mean_f1 = mean_metric(f1_values)
    return StrategyAggregate(
        strategy=strategy,
        collection=collection,
        query_count=len(rows),
        mean_precision=round(mean_p, 4),
        mean_recall=round(mean_r, 4),
        mean_f1=round(mean_f1, 4),
    )


def recommend_strategy(
    fixed_agg: StrategyAggregate,
    sentence_agg: StrategyAggregate,
    *,
    fixed_chunk_count: int,
    sentence_chunk_count: int,
) -> dict[str, Any]:
    if fixed_agg.mean_precision > sentence_agg.mean_precision:
        winner: StrategyName = "fixed"
        reason = (
            f"Fixed-size chunks achieved higher mean precision ({fixed_agg.mean_precision:.4f} vs "
            f"{sentence_agg.mean_precision:.4f}) with equal mean recall ({fixed_agg.mean_recall:.4f})."
        )
    elif sentence_agg.mean_precision > fixed_agg.mean_precision:
        winner = "sentence"
        reason = (
            f"Sentence chunks achieved higher mean precision ({sentence_agg.mean_precision:.4f} vs "
            f"{fixed_agg.mean_precision:.4f}) with mean recall {sentence_agg.mean_recall:.4f} vs "
            f"{fixed_agg.mean_recall:.4f}."
        )
    elif fixed_agg.mean_recall > sentence_agg.mean_recall:
        winner = "fixed"
        reason = (
            f"Mean precision tied at {fixed_agg.mean_precision:.4f}; fixed-size chunks win on mean recall "
            f"({fixed_agg.mean_recall:.4f} vs {sentence_agg.mean_recall:.4f})."
        )
    elif sentence_agg.mean_recall > fixed_agg.mean_recall:
        winner = "sentence"
        reason = (
            f"Mean precision tied at {fixed_agg.mean_precision:.4f}; sentence chunks win on mean recall "
            f"({sentence_agg.mean_recall:.4f} vs {fixed_agg.mean_recall:.4f})."
        )
    else:
        winner = "fixed"
        reason = (
            f"Mean precision and recall both tied at {fixed_agg.mean_precision:.4f} / "
            f"{fixed_agg.mean_recall:.4f}; fixed-size indexing is preferred for fewer chunks "
            f"({fixed_chunk_count} vs {sentence_chunk_count}) and simpler overlap handling."
        )

    return {
        "recommended_strategy": winner,
        "recommended_collection": STRATEGY_TO_COLLECTION[winner],
        "rationale_sentences": reason,
    }


def run_full_evaluation(
    *,
    persist_dir: Path | str = DEFAULT_CHROMA_DIR,
    ground_truth_path: Path | None = None,
    embedder: SentenceTransformer | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    gt_doc = load_ground_truth(ground_truth_path)
    entries = parse_ground_truth_entries(gt_doc)
    validate_evaluation_queries_match_task4(entries)

    k = top_k if top_k is not None else int(gt_doc.get("top_k", TASK4_TOP_K))
    model = embedder or get_embedder()
    client = get_chroma_client(persist_dir)

    per_query: list[dict[str, Any]] = []
    by_strategy: dict[StrategyName, list[QueryStrategyMetrics]] = {"fixed": [], "sentence": []}

    for entry in entries:
        for strategy in ("fixed", "sentence"):
            collection = client.get_collection(STRATEGY_TO_COLLECTION[strategy])
            metrics = evaluate_query_for_strategy(
                entry,
                strategy=strategy,
                collection=collection,
                embedder=model,
                top_k=k,
            )
            by_strategy[strategy].append(metrics)
            per_query.append(metrics.to_dict())

    fixed_agg = aggregate_strategy_metrics(by_strategy["fixed"])
    sentence_agg = aggregate_strategy_metrics(by_strategy["sentence"])

    fixed_col = client.get_collection(COLLECTION_FIXED)
    sentence_col = client.get_collection(COLLECTION_SENTENCE)
    recommendation = recommend_strategy(
        fixed_agg,
        sentence_agg,
        fixed_chunk_count=fixed_col.count(),
        sentence_chunk_count=sentence_col.count(),
    )

    return {
        "embedding_model": EMBEDDING_MODEL_NAME,
        "top_k": k,
        "ground_truth_path": str((ground_truth_path or GROUND_TRUTH_PATH).resolve()),
        "per_query_results": per_query,
        "aggregates": {
            "fixed": fixed_agg.to_dict(),
            "sentence": sentence_agg.to_dict(),
        },
        "recommendation": recommendation,
    }


def render_markdown_report(evaluation: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Task 5 — Document-level precision and recall",
        "",
        f"- **Embedding model:** {evaluation['embedding_model']}",
        f"- **Top-k:** {evaluation['top_k']}",
        f"- **Ground truth:** {evaluation['ground_truth_path']}",
        "",
    ]

    rec = evaluation["recommendation"]
    lines.extend(
        [
            "## Recommendation",
            "",
            f"**Recommended strategy:** `{rec['recommended_strategy']}` (`{rec['recommended_collection']}`)",
            "",
            rec["rationale_sentences"],
            "",
        ]
    )

    for strategy in ("fixed", "sentence"):
        agg = evaluation["aggregates"][strategy]
        lines.extend(
            [
                f"## Aggregate — {strategy} (`{agg['collection']}`)",
                "",
                f"- Mean precision: **{agg['mean_precision']:.4f}**",
                f"- Mean recall: **{agg['mean_recall']:.4f}**",
                f"- Mean F1 (supplemental): **{agg['mean_f1']:.4f}**",
                "",
            ]
        )

    rows = evaluation["per_query_results"]
    for entry in rows:
        if entry["strategy"] != "fixed":
            continue
        query_id = entry["query_id"]
        sentence_row = next(
            r for r in rows if r["query_id"] == query_id and r["strategy"] == "sentence"
        )
        lines.extend(
            [
                f"### {entry['topic']} — `{query_id}`",
                "",
                f"**Query:** {entry['query_text']}",
                "",
                f"**Relevant docs:** `{set(entry['relevant_document_ids'])}`",
                "",
                f"#### Fixed (`{entry['collection']}`)",
                "",
                f"- Retrieved chunks: `{[c['chunk_id'] for c in entry['retrieved_chunks']]}`",
                f"- Retrieved parent docs (deduped): `{set(entry['retrieved_parent_document_ids'])}`",
                f"- TP = {entry['true_positives']}, FP = {entry['false_positives']}, FN = {entry['false_negatives']}",
                f"- {entry['precision_expression']}",
                f"- {entry['recall_expression']}",
                "",
                f"#### Sentence (`{sentence_row['collection']}`)",
                "",
                f"- Retrieved chunks: `{[c['chunk_id'] for c in sentence_row['retrieved_chunks']]}`",
                f"- Retrieved parent docs (deduped): `{set(sentence_row['retrieved_parent_document_ids'])}`",
                f"- TP = {sentence_row['true_positives']}, FP = {sentence_row['false_positives']}, FN = {sentence_row['false_negatives']}",
                f"- {sentence_row['precision_expression']}",
                f"- {sentence_row['recall_expression']}",
                "",
            ]
        )

    return "\n".join(lines)

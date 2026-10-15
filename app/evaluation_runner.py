"""Part 3 Task 13 — run 15-query evaluation through guarded crew path."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from app.guardrails import run_guarded_support_crew_kickoff
from app.mock_judge import JUDGE_RUBRIC_VERSION, MOCK_JUDGE_PROMPT, SCORE_MAX, SCORE_MIN, score_with_mock_judge

EVALUATION_QUERIES_PATH = Path(__file__).resolve().parent / "data" / "evaluation_queries.json"


def load_evaluation_queries(path: Path | None = None) -> list[dict[str, Any]]:
    payload = json.loads((path or EVALUATION_QUERIES_PATH).read_text(encoding="utf-8"))
    queries = payload["queries"]
    if len(queries) != 15:
        raise ValueError(f"Expected 15 evaluation queries, got {len(queries)}")
    return queries


def _extract_run_artifacts(outcome: dict[str, Any]) -> dict[str, Any]:
    structured = outcome.get("structured_response") or {}
    if outcome.get("guardrail_blocked"):
        answer = str(outcome.get("assistant_refusal") or "")
    else:
        answer = str(structured.get("answer") or outcome.get("kickoff_output") or "")

    rag_trace = outcome.get("rag_tool_trace") or []
    order_trace = outcome.get("order_tool_trace") or []
    supporting_context = ""
    retrieved_doc_ids: list[str] = []
    if rag_trace:
        payload = rag_trace[-1].get("payload") or {}
        supporting_context = str(payload.get("supporting_context") or "")
        for chunk in payload.get("retrieved_chunks") or []:
            doc_id = chunk.get("document_id")
            if doc_id:
                retrieved_doc_ids.append(doc_id)

    sources = list(structured.get("sources") or [])
    if not sources and retrieved_doc_ids:
        sources = sorted(set(retrieved_doc_ids))

    return {
        "answer": answer,
        "structured": structured,
        "guardrail_blocked": bool(outcome.get("guardrail_blocked")),
        "guardrail_type": outcome.get("guardrail_type"),
        "fallback": bool(structured.get("fallback")),
        "sources": sources,
        "supporting_context": supporting_context,
        "order_tool_payload": (order_trace[-1].get("payload") if order_trace else None),
        "kickoff_used": bool(outcome.get("kickoff_used")),
    }


def evaluate_single_query(case: dict[str, Any]) -> dict[str, Any]:
    outcome = run_guarded_support_crew_kickoff(case["query"])
    artifacts = _extract_run_artifacts(outcome)
    scores = score_with_mock_judge(
        query=case["query"],
        answer=artifacts["answer"],
        expected_mode=case["expected_mode"],
        expected_facts=list(case.get("expected_facts") or []),
        expected_kb_ids=list(case.get("expected_kb_ids") or []),
        forbidden_answer_facts=list(case.get("forbidden_answer_facts") or []),
        guardrail_blocked=artifacts["guardrail_blocked"],
        guardrail_type=artifacts.get("guardrail_type"),
        fallback=artifacts["fallback"],
        actual_sources=artifacts["sources"],
        supporting_context=artifacts["supporting_context"],
    )
    return {
        "query_id": case["query_id"],
        "query": case["query"],
        "topic": case["topic"],
        "expected_mode": case["expected_mode"],
        "expected_kb_ids": case.get("expected_kb_ids") or [],
        "expected_facts": case.get("expected_facts") or [],
        "actual_answer": artifacts["answer"],
        "actual_sources": artifacts["sources"],
        "supporting_context_preview": artifacts["supporting_context"][:400],
        "order_tool_payload": artifacts["order_tool_payload"],
        "guardrail_blocked": artifacts["guardrail_blocked"],
        "guardrail_type": artifacts.get("guardrail_type"),
        "kickoff_used": artifacts["kickoff_used"],
        "scores": scores.as_dict(),
    }


def compute_averages(results: list[dict[str, Any]]) -> dict[str, float]:
    def avg(key: str) -> float:
        values = [float(r["scores"][key]) for r in results]
        return round(mean(values), 4)

    return {
        "accuracy": avg("accuracy"),
        "grounding": avg("grounding"),
        "completeness": avg("completeness"),
        "safety": avg("safety"),
    }


def run_evaluation_suite(path: Path | None = None) -> dict[str, Any]:
    cases = load_evaluation_queries(path)
    results = [evaluate_single_query(case) for case in cases]
    averages = compute_averages(results)
    return {
        "judge_rubric_version": JUDGE_RUBRIC_VERSION,
        "mock_judge_prompt": MOCK_JUDGE_PROMPT,
        "score_scale": f"{SCORE_MIN}-{SCORE_MAX}",
        "query_count": len(results),
        "results": results,
        "averages": averages,
    }


def format_evaluation_report(suite: dict[str, Any]) -> str:
    lines = [
        "# Task 13 evaluation report",
        "",
        f"Judge: `{suite['judge_rubric_version']}` · Scale: **{suite['score_scale']}**",
        "",
        "| Query ID | Topic | Accuracy | Grounding | Completeness | Safety |",
        "|----------|-------|----------|-----------|--------------|--------|",
    ]
    for row in suite["results"]:
        s = row["scores"]
        lines.append(
            f"| {row['query_id']} | {row['topic'][:40]} | {s['accuracy']} | {s['grounding']} | "
            f"{s['completeness']} | {s['safety']} |"
        )
    avg = suite["averages"]
    lines.extend(
        [
            "",
            "## Averages",
            "",
            f"- Accuracy: **{avg['accuracy']}**",
            f"- Grounding: **{avg['grounding']}**",
            f"- Completeness: **{avg['completeness']}**",
            f"- Safety: **{avg['safety']}**",
            "",
        ]
    )
    return "\n".join(lines)

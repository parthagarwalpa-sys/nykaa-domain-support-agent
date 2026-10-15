# Step 6 — Part 1 Task 5: Chunking strategy precision/recall comparison

**Date:** 2026-10-14  
**Verdict:** STEP_6_TASK_5_COMPLETE

## Configuration

| Item | Value |
|------|--------|
| Collections | `nykaa_fixed_chunks`, `nykaa_sentence_chunks` |
| Queries | Task 4 `DEMONSTRATION_IN_SCOPE_QUERIES` (5 queries, identical text) |
| Top-k | 3 |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2`, normalized |
| Ground truth | `app/data/retrieval_ground_truth.json` (manual KB labels) |
| Task 4 fallback threshold | **Not applied** (retrieval quality only) |

## Aggregates

| Strategy | Mean precision | Mean recall | Mean F1 (supplemental) |
|----------|---------------:|------------:|-----------------------:|
| Fixed | 0.6667 | 1.0000 | 0.7667 |
| Sentence | 0.6667 | 1.0000 | 0.7667 |

## Recommendation

**Use `nykaa_fixed_chunks` for Part 2.** Mean precision and recall tied at **0.6667 / 1.0000** on all five evaluation queries; fixed-size indexing is preferred because it uses **39** chunks versus **49** with the same deduplicated parent-document retrieval sets.

## Artifacts

- [`retrieval_ground_truth.json`](retrieval_ground_truth.json)
- [`precision_recall_results.json`](precision_recall_results.json)
- [`precision_recall_report.md`](precision_recall_report.md) — per-query TP/FP/FN arithmetic
- [`pytest_task5.txt`](pytest_task5.txt) — 11 passed
- [`pytest_regression.txt`](pytest_regression.txt) — 41 passed (Tasks 1–4 + Step 1B, pre–Task 5)
- [`pytest_full_regression.txt`](pytest_full_regression.txt) — 52 passed (incl. Task 5)
- [`pip_check.txt`](pip_check.txt)

## Official brief

`docs/MASAI_OFFICIAL_BRIEF.md` unchanged (SHA-256 `833020E559002D425710BCFC56A6BBA5F03B9A6D786567E0C39035FEF79CFADD`).

# Step 17 — Part 4 Task 16: In-memory grounded-generation cache

**Date:** 2026-10-15  
**Modules:** `app/grounded_cache.py`, `app/grounded_generation.py`

## Scope

In-process cache for `generate_grounded_answer` only (Task 4 retrieval + grounded answer). Not full FastAPI responses or order-status lookups.

## Key format

`{collection_name}|k={top_k}|{normalized_query}`

Normalization: strip, collapse whitespace, lowercase (punctuation unchanged).

## Miss / hit evidence

| Request | `cache_hit` | `grounded_generation_execution_count` |
|---------|-------------|----------------------------------------|
| First | `false` (`first_request_cache_miss.json`) | 0 → 1 |
| Second identical | `true` (`second_request_cache_hit.json`) | stays 1 |

See `call_counter_before_after.json`, `identical_result_proof.json`, `equivalent_normalized_query_hit.json`.

## Invalidation

`clear_grounded_cache()` resets entries and counters. Use after KB/collection changes; no add-document API in this repository.

## Tests

- Task 16: 15 passed (`pytest_task16.txt`)
- Full suite: 208 passed (`pytest_full_regression.txt`)
- `pip check`: clean (`pip_check.txt`)

## Official brief

SHA-256 unchanged: `833020E559002D425710BCFC56A6BBA5F03B9A6D786567E0C39035FEF79CFADD`

**Verdict:** `STEP_17_TASK_16_COMPLETE`

# Step 16 — Part 4 Task 15: Governance

**Date:** 2026-10-15  
**Module:** `app/governance.py`

## Least autonomy

See `agent_capability_matrix.json`. Only Order Lookup Agent holds `lookup_order_status`.

## Risk

**Medium** — rationale in `risk_classification.json`.

## Runtime budget

- Formula: `ceil(len(text)/4)` estimated tokens  
- Cap: **1024**  
- Oversized demo: `demo_oversized_request_rejection.json` (kickoff/tools/autogen skipped)

## Tests

- Task 15: 20 passed (`pytest_task15.txt`)
- Full suite: 193 passed (`pytest_full_regression.txt`)
- `pip check`: clean

## Official brief

SHA-256 unchanged: `833020E559002D425710BCFC56A6BBA5F03B9A6D786567E0C39035FEF79CFADD`

**Verdict:** `STEP_16_TASK_15_COMPLETE`

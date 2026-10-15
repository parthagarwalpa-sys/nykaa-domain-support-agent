# Step 7 — Part 2 Task 6: Order status lookup and escalation score

**Date:** 2026-10-15  
**Verdict:** STEP_7_TASK_6_COMPLETE

## Function

- **Name:** `check_order_status(record_id: str) -> dict`
- **Location:** `app/order_status.py`
- **Data source:** `dataset.ORDERS` (Task 1, seed `20261013`, unmodified)

## Escalation formula

```
delayed_signal   = 1.0 if delayed_shipment else 0.0
normalized_age   = days_since_created / 30
escalation_score = clamp_0_1(0.6 * delayed_signal + 0.4 * normalized_age)
```

| Weight | Value |
|--------|------:|
| delayed_shipment | 0.6 |
| normalized_age | 0.4 |

## Threshold

| Statistic | Value |
|-----------|------:|
| Percentile used | 80th |
| Threshold | **0.6160** |
| Score min / p50 / p80 / max | 0.0133 / 0.2067 / 0.6160 / 0.9867 |

**Rationale:** The 80th percentile on the deterministic 40-order cohort flags roughly the highest-risk fifth of tickets for human escalation, using the combined delay+age score rather than a fixed guess such as 0.5.

## Samples

See [`escalation_evidence.json`](escalation_evidence.json) for full JSON.

| Case | record_id | escalation_score | recommended |
|------|-----------|------------------:|-------------|
| Valid (typical) | NYK-20261013-0001 | 0.1333 | false |
| Escalated | NYK-20261013-0005 | 0.9067 | true |
| Not escalated | NYK-20261013-0014 | 0.0133 | false |
| Unknown ID | NYK-DOES-NOT-EXIST | — | `OrderRecordNotFoundError` |

## Tests

| Command | Result |
|---------|--------|
| `pytest tests/test_order_status.py -v` | 11 passed — [`pytest_task6.txt`](pytest_task6.txt) |
| Part 1 + Step 1B regression | 52 passed — [`pytest_regression.txt`](pytest_regression.txt) |
| `pip check` | clean — [`pip_check.txt`](pip_check.txt) |

## Official brief

`docs/MASAI_OFFICIAL_BRIEF.md` unchanged (SHA-256 `833020E559002D425710BCFC56A6BBA5F03B9A6D786567E0C39035FEF79CFADD`).

# Step 11 — Part 2 Task 10: Guardrails

**Date:** 2026-10-15  
**Module:** `app/guardrails.py`  
**Integration:** `run_guarded_support_crew_kickoff()`; session path in `app/support_session.py`

## Demonstrations (fabricated data only)

| Artifact | Purpose |
|----------|---------|
| `demo_phone_masking.json` | Phone `9876543210` masked; downstream `sanitized_query` has no raw digits |
| `demo_card_last4_masking.json` | `card ending 5678` → `****` |
| `demo_negative_four_digit_no_mask.json` | Year/price/PIN unchanged |
| `demo_injection_block.json` | Attack blocked; `kickoff_used=false` |
| `demo_grounded_policy_pass.json` | Validator accepts RAG-aligned policy response |
| `demo_ungrounded_policy_refusal.json` | Fabricated policy claim rejected |
| `demo_grounded_order_pass.json` | Guarded order kickoff passes |
| `demo_fabricated_order_refusal.json` | Wrong `status` vs Task 6 payload rejected |

## Tests

- Task 10: `pytest_task10.txt` — **18 passed**
- Full regression: `pytest_full_regression.txt` — **111 passed**
- Dependencies: `pip_check.txt` — **No broken requirements found**

## Official brief

`docs/MASAI_OFFICIAL_BRIEF.md` SHA-256 unchanged:  
`833020E559002D425710BCFC56A6BBA5F03B9A6D786567E0C39035FEF79CFADD`

## Limitations

- Name/address free-text masking out of scope (Masai brief).
- Injection rules are explicit patterns only.
- Output groundedness uses tool traces (no LLM judge).

**Verdict:** `STEP_11_TASK_10_COMPLETE`

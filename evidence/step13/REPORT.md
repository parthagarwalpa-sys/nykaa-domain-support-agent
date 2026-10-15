# Step 13 — Part 3 Task 12: Structured JSON-Lines logging

**Date:** 2026-10-15  
**Module:** `app/request_logging.py`  
**Runtime log:** `logs/requests.jsonl` (gitignored)

## Integration

| Transport | Path | One JSONL entry per |
|-----------|------|---------------------|
| HTTP | `POST /ask` | `/ask` request |
| HTTP | `POST /order-status` | lookup request |
| WebSocket | `/ws/chat` | inbound chat message |

PII: `sanitize_for_log()` → Task 10 `prepare_sanitized_input()` before write.

## Evidence artifacts

- `sample_success_entry.json`
- `masked_phone_log_entry.json`, `masked_card_log_entry.json`
- `injection_block_log_entry.json`, `groundedness_refusal_log_entry.json`
- `websocket_logged_entry.json`
- `trace_and_timing_evidence.json`, `sample_requests.jsonl`
- `pytest_task12.txt` — 18 passed
- `pytest_full_regression.txt` — 145 passed
- `pip_check.txt` — clean

## Official brief

SHA-256 unchanged: `833020E559002D425710BCFC56A6BBA5F03B9A6D786567E0C39035FEF79CFADD`

**Verdict:** `STEP_13_TASK_12_COMPLETE`

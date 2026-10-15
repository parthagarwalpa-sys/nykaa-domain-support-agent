# NYKAA CAPSTONE — ACCEPTANCE CHECKLIST / EXECUTION TRACKER

**Source of authority:** `MASAI_OFFICIAL_BRIEF.md`. **Status at creation:** ALL ITEMS PENDING.  
For each checklist item, add (a) test/command, (b) file location, (c) evidence transcript, (d) verified-by/date. Do not mark `[x]` based solely on a Cursor summary.

Status vocabulary: `PENDING` → `IMPLEMENTED` → `TESTED` → `VERIFIED`. This checklist uses `[x]` only at VERIFIED.

## Cross-cutting initial feasibility and compliance gates

- [x] G00 Official Masai brief preserved unchanged; SHA checked; Nykaa chosen.
- [x] G01 Independent, self-contained repository; clean Python environment; versions pinned.
- [x] G02 Custom CrewAI `BaseLLM` produces a **real** `.kickoff()` tool invocation; tool counter / output trace proves it.
- [x] G03 AutoGen RoundRobinGroupChat runs a two-agent mock review with a registered structured Pydantic verdict.
- [ ] G04 `MOCK_LLM` paths require zero API keys and no runtime network access; CrewAI telemetry disabled **before** crew init. *(Step 1B: API keys + telemetry pre-init verified; absolute zero-network not packet-verified.)*
- [ ] G05 All original content fictional, independently authored for this brief; no real sensitive data.

## Part 1 — Dataset Design & RAG Core (30 marks)

### T01 Dataset
- [x] `dataset.py` exports `ORDERS` containing >=40 seeded deterministic records.
- [x] Required fields exist: record_id, category, status, order_value_inr, days_since_created, delayed_shipment.
- [x] Categories Apparel/Electronics/Home/Footwear/Beauty each have >=3 rows.
- [x] Statuses Placed/Shipped/Delivered/Returned/Refunded each appear >=1 time.
- [x] days_since_created integer range 0–30; record IDs unique; plausible order value range.
- [x] delayed_shipment True is 10–30%; generated via seed/weights, not individual hand edits.
- [x] Console report prints counts by category/status and delayed percentage.
- [x] README documents exact seed, category/status weights, order-value range and one-sentence rationale.

### T02 Knowledge base
- [x] >=12 independent documents each 2–5 sentences, original fictional demo policies.
- [x] Every topic covered: returns by category; COD refunds; delivery SLAs; reverse pickup; warranties by category; cancellation; loyalty points; payment failure/retry; size exchange; damage claims; international restrictions; support escalation.

### T03 Chunking and vector stores
- [x] Fixed-size-with-overlap chunking implemented.
- [x] Sentence-based chunking implemented.
- [x] Every chunk embedded using a local SentenceTransformers model.
- [x] Two *separate* ChromaDB collections upsert chunks; parent doc IDs kept.
- [x] Sample query sensibly retrieves documents from both collections.

### T04 Grounding and calibrated fallback
- [x] Retrieve top-k context and generate only grounded answers.
- [x] Measure top-1 cosine values of >=3 in-scope and >=2 deliberately out-of-scope queries.
- [x] Threshold chosen from actual measurements, not arbitrary preset; values and threshold in README.
- [x] >=5 in-scope grounded demos and >=1 out-of-scope fallback `I don't know` demonstrated.

**Verified evidence (2026-10-14):** `app/grounded_generation.py`, `app/data/retrieval_threshold.json`, `scripts/calibrate_retrieval_threshold.py`, `scripts/run_grounded_generation_demo.py`, `tests/test_grounded_generation.py` (12 passed); `evidence/step5/threshold_calibration.json`, `grounded_generation_examples.json`, `pytest_regression.txt`, `pip_check.txt`, `REPORT.md`. Collection `nykaa_sentence_chunks` (provisional); top-k=3; L2 gate **1.1129**; regression 40/40 pytest + `pip check` clean.

### T05 Compare retrieval strategies
- [x] Identical >=5 queries evaluated on both collections.
- [x] Chunk parent IDs deduplicated at document level before scoring.
- [x] Per-query TP/FP/FN and precision/recall arithmetic visible for **both** collections.
- [x] Two/three-sentence choice of recommended chunker cites actual results.

**Verified evidence (2026-10-14):** `app/retrieval_evaluation.py`, `app/data/retrieval_ground_truth.json`, `scripts/run_retrieval_precision_recall.py`, `tests/test_retrieval_evaluation.py` (11 passed); `evidence/step6/` (`retrieval_ground_truth.json`, `precision_recall_results.json`, `precision_recall_report.md`, pytest + regression + `pip check`). Top-k=3; mean P/R **0.6667 / 1.0000** both strategies; recommend **`nykaa_fixed_chunks`** on tie-break (39 vs 49 chunks). Task 5 **11/11**; Tasks 1–4 + Step 1B regression **41/41**; `pip check` clean.

## Part 2 — CrewAI + tools + memory + guardrails (30 marks)

### T06 Escalation lookup
- [x] `check_order_status(record_id: str) -> dict` returns status, order_value_inr, escalation_score in [0,1].
- [x] Score **combines** delayed_shipment and normalized days_since_created, not only a boolean.
- [x] Exact formula and chosen escalation threshold stated and justified using generated distribution.
- [x] Valid and invalid IDs; boundary-score tests pass.

**Verified evidence (2026-10-15):** `app/order_status.py`, `scripts/lookup_order_demo.py`, `scripts/generate_escalation_evidence.py`, `tests/test_order_status.py` (11 passed); `evidence/step7/` (`escalation_evidence.json`, pytest + regression + `pip check`, `REPORT.md`). Formula `0.6×delay + 0.4×(days/30)`; threshold **0.6160** = p80 of scores on ORDERS; unknown ID → `OrderRecordNotFoundError`. Regression **52/52** + Task 6 **11/11**.

### T07 CrewAI orchestration
- [x] >=3 real CrewAI agents: Retrieval/RAG tool, Lookup/status tool, Composer.
- [x] `.kickoff()` actually runs the crew.
- [x] Separate policy query proves real RAG tool call.
- [x] Separate order query proves real status lookup tool call.
- [x] Tool counts/traces captured, avoiding name-based dispatcher and template `Observation:` parser bugs.

**Verified evidence (2026-10-15):** `app/support_crew.py`, `app/crew_tools.py`, `app/nykaa_mock_llm.py`, `scripts/run_support_crew_demos.py`, `tests/test_support_crew.py` (10 passed); `evidence/step8/`. RAG collection **`nykaa_fixed_chunks`**; policy demo RAG=1/order=0; order demo RAG=0/order=1; Task 6 lookup (not smoke data). Regression **73/73** + `pip check` clean.

### T08 LangChain session memory
- [x] In-process session-based LangChain memory used.
- [x] Multi-turn transcript demonstrates context retained in same session.
- [x] Separate fresh-session transcript demonstrates no leaked memory.

**Verified evidence (2026-10-15):** `app/memory.py`, `app/support_session.py`, `scripts/run_memory_demos.py`, `tests/test_session_memory.py` (11 passed); `evidence/step9/` transcripts + store summary. `InMemoryChatMessageHistory` + `RunnableWithMessageHistory`; session A retains order context for escalation follow-up; session B missing-context. Regression **84/84** + `pip check` clean.

### T09 Structured output
- [x] Every crew response validated at runtime against a defined Pydantic BaseModel (`response_format`).
- [x] Invalid model output produces a handled validation failure instead of silent success.

**Verified evidence (2026-10-15):** `app/crew_schemas.py`, `app/structured_output.py`, `app/support_crew.py` (`output_pydantic=SupportCrewResponse`), `tests/test_structured_crew_output.py` (9 passed); `evidence/step10/`. Policy/order structured demos + invalid `record_id` rejection. Regression **93/93** + `pip check` clean.

### T10 Guardrails
- [x] Input mask fires on synthetic phone number.
- [x] Input mask fires on synthetic payment-card **last-four-digits** in context.
- [x] Prompt injection detector triggers on deliberate test input.
- [x] Output-side groundedness guard refuses unsupported claims; deliberate test transcript.
- [x] All supported sensitive values remain masked in the complete flow.

**Verified evidence (2026-10-15):** `app/guardrails.py`, guarded entry via `run_guarded_support_crew_kickoff` + `app/support_session.py`; `tests/test_guardrails.py` (18 passed); `evidence/step11/`. Phone `9876543210` → `******3210`; card phrase `card ending ####` → `****`; injection block; policy/order groundedness pass & refusal demos. Full regression **111/111** + `pip check` clean.

## Part 3 — API + observability + evaluation (20 marks)

### T11 FastAPI
- [x] >=2 working HTTP endpoints (Masai e.g. `POST /ask`, `POST /add-document` — implemented as `POST /ask` + `POST /order-status`, plus `GET /health`).
- [x] Pydantic request and response models on HTTP endpoints.
- [x] Second HTTP route satisfies “≥2 endpoints” without requiring `/add-document` (Masai lists it as an example only).
- [x] Working WebSocket endpoint supports multi-turn chat.
- [x] `WebSocketDisconnect` handled; new client still works after mid-session disconnect.

**Verified evidence (2026-10-15):** `app/main.py`, `app/api_schemas.py`; routes `POST /ask`, `POST /order-status`, `GET /health`, `WS /ws/chat`; guarded flow via `run_session_turn`; `tests/test_fastapi_api.py` (16 passed); `evidence/step12/`. WebSocket crew runs in `asyncio.to_thread`. Full regression **127/127** + `pip check` clean.

### T12 Structured logging
- [x] Every request produces exactly one structured JSONL event with trace ID and timing information.
- [x] Known synthetic phone number absent in raw log file.
- [x] Known synthetic card last-four value absent in raw log file.
- [x] Error and rejected-request paths also log safely without raw masked PII.

**Verified evidence (2026-10-15):** `app/request_logging.py` → `logs/requests.jsonl` (override `NYKAA_REQUEST_LOG_PATH` in tests); integrated in `POST /ask`, `POST /order-status`, `WS /ws/chat`; `tests/test_request_logging.py` (18 passed); `evidence/step13/`. Full regression **145 passed** + `pip check` clean.

### T13 Mock judge evaluation
- [x] Exactly/at least 15 case evaluation suite as requested: >=1 touching each of 12 topics + >=2 out-of-scope/edge cases.
- [x] Documented LLM-as-judge prompt runs in deterministic `MOCK_LLM` mode.
- [x] Each of 15 has four results: Accuracy, Grounding, Completeness, Safety.
- [x] Four averages calculated and printed.
- [x] Evidence records actual query, expected/source policy, result, and judge rationale/rule.

**Verified evidence (2026-10-15):** `app/data/evaluation_queries.json`, `app/mock_judge.py`, `app/evaluation_runner.py`; guarded `run_guarded_support_crew_kickoff` path; `tests/test_evaluation_task13.py` (13 passed); `evidence/step14/`. Averages — Accuracy **1.0**, Grounding **0.937**, Completeness **1.0**, Safety **1.0**. Full regression **158 passed** + `pip check` clean.

## Part 4 — Resilience + governance (20 marks)

### T14 AutoGen review
- [x] Two agents execute via actual `RoundRobinGroupChat(max_turns=2)` or equivalent compliant termination.
- [x] Final editor uses `output_content_type=ReviewVerdict` with fields approved/bool, final_answer/str, reason/str.
- [x] Team includes required `custom_message_types=[StructuredMessage[ReviewVerdict]]` under installed API.
- [x] Stage receives Composer draft and original retrieved context.
- [x] One case approves draft *unchanged* with typed verdict.
- [x] One deliberate unsupported claim is revised with typed verdict.

**Verified evidence (2026-10-15):** `app/autogen_review.py`, `app/schemas.ReviewVerdict`, integration in `app/guardrails.py` post-groundedness; `tests/test_autogen_review_task14.py` (15 passed); `evidence/step15/`. Full regression **173 passed** + `pip check` clean.

### T15 Four-layer governance demonstration
- [x] Only Lookup Agent can call `check_order_status` (role wiring plus demonstration).
- [x] Low/Medium/High risk category selected with 1-paragraph justification for this system.
- [x] Per-request token/cost budget gate enforced.
- [x] Deliberately oversized request rejected, not silently processed.
- [x] Brief's four-layer AI-governance framing explained; don't invent unlisted acceptance gates.

**Verified evidence (2026-10-15):** `app/governance.py`, budget gate in `app/guardrails.py`; `tests/test_governance_task15.py` (20 passed); `evidence/step16/`. Risk **Medium**; cap **1024 estimated_tokens** (`ceil(len/4)`). Full regression **193 passed** + `pip check` clean.

### T16 Caching
- [x] In-memory cache keyed by normalized query text for grounded-generation step.
- [x] Repeated same query gets genuine cache hit.
- [x] Before/after call counter or timing demonstrates redundant generation/tool call avoided.
- [x] Cache invalidation prevents stale KB answers after add-document (quality safeguard).

**Verified evidence (2026-10-15):** `app/grounded_cache.py`, cache wrap in `app/grounded_generation.generate_grounded_answer`; `tests/test_grounded_cache_task16.py` (15 passed); `evidence/step17/`. `grounded_generation_execution_count` unchanged on second identical query; `clear_grounded_cache()` for KB refresh (no add-document endpoint in repo). Full regression **208 passed** + `pip check` clean — see `evidence/step17/REPORT.md`.

## Final submission gate

- [x] All 16 tasks verified and evidenced in repository text/code; no unverified checkbox marked complete. *(See `docs/FINAL_SUBMISSION_AUDIT.md`, 2026-10-15.)*
- [x] `README.md` starts by stating **Nykaa (E-commerce & Retail)** track.
- [x] README reproduces dataset seed/weights/range; cosine calibration; precision/recall; escalation formula; test procedures; mock telemetry disablement.
- [x] Clean fresh checkout installs and runs from documented setup steps. *(Fresh venv: `evidence/audit/REPORT.md` — 208 pytest passed.)*
- [x] Graded transcripts generated with deterministic `MOCK_LLM`, no API keys. *(First-time HF model download may use network; not the same as LLM API calls.)*
- [x] No real customer information, keys, tokens or local `.env` committed.
- [x] No unrequested external deliverables (slides/screenshots/videos/PDFs).
- [ ] One public GitHub repository contains everything and link submitted before confirmed deadline. *(Workspace not a git repo at audit time — `docs/FINAL_SUBMISSION_CHECKLIST.md`.)*

## Progress log (fill during execution)

| Date | Task/gate | Status | Command/test | Evidence path | Notes/blocker |
|---|---|---|---|---|---|
| 2026-10-12 | Planning artifacts | DOCUMENTED, NOT TESTED | n/a | three Markdown documents | Implementation pending |
| 2026-10-13 | Step 1B gates G00–G03 (+ partial G04) | VERIFIED | `pytest tests/test_step1b_smoke.py -v` | `evidence/step1b/` | Initial pass; protobuf workaround pending |
| 2026-10-13 | Step 1B closure (deps + primary `.venv`) | VERIFIED | `pip install -r requirements.in`; `pip check`; `pytest tests/test_step1b_smoke.py -v` | `evidence/step1b/REPORT.md`, `pip_check_final.txt`, `pytest_step1b_smoke_final.txt` | `protobuf==5.29.6`, `googleapis-common-protos==1.75.0`; G04 network packet-test still pending |
| 2026-10-13 | Part 1 T01 dataset | VERIFIED | `python dataset.py`; `pytest tests/test_dataset.py -v` | `evidence/step2/` | seed `20261013`, 40 ORDERS, delayed 22.5% |
| 2026-10-13 | Part 1 T02 policy drafts | DRAFT_PENDING_HUMAN_REVIEW | `pytest tests/test_knowledge_base_drafts.py -v` | `evidence/step3/` | 12 KB files; not marked T02 complete |
| 2026-10-14 | Part 1 T02 finalized | VERIFIED | KB edits + full pytest/pip check | `evidence/step3/KNOWLEDGE_BASE_FINAL_REVIEW.md` | Human-approved edits to KB-001, KB-007, KB-010 |
| 2026-10-14 | Part 1 T03 RAG index | VERIFIED | `pytest tests/test_rag_index.py`; `scripts/rebuild_kb_index.py` | `evidence/step4/` | MiniLM-L6-v2; 39 fixed + 49 sentence chunks |

## Working protocol

1. At each step, read Masai brief first and relevant SSOT section second.
2. Implement only the next gated capability, run its test, save sanitized text evidence.
3. Mark VERIFIED only after observing the test and mapping its output to a required acceptance item.
4. If blocked, record dependency versions, actual failure and next reproduction step. Do not switch to an undocumented simulated pass.
5. Maintain a concise technical rationale for each verified component, including implementation decisions and known limitations.

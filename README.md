# Nykaa (E-commerce & Retail) — Masai Final Capstone

> **Track:** Nykaa (E-commerce & Retail) domain support agent (CrewAI + AutoGen + local RAG).  
> **Status:** Parts 1–4 complete (Tasks 1–16 verified in-repo). Graded execution uses deterministic **MOCK_LLM** with telemetry disabled; see [`docs/FINAL_SUBMISSION_AUDIT.md`](docs/FINAL_SUBMISSION_AUDIT.md) for the latest acceptance audit.

This repository is an original, self-contained **fictional retail support** project. It is not affiliated with Nykaa and does not use real customer data.

## Authority

- [`docs/MASAI_OFFICIAL_BRIEF.md`](docs/MASAI_OFFICIAL_BRIEF.md) — supreme specification (unchanged).
- [`docs/NYKAA_IMPLEMENTATION_SSOT.md`](docs/NYKAA_IMPLEMENTATION_SSOT.md) — engineering plan.
- [`docs/NYKAA_ACCEPTANCE_CHECKLIST.md`](docs/NYKAA_ACCEPTANCE_CHECKLIST.md) — verified evidence tracker.

## Environment (verified Step 1B)

- **Graded LLM path:** deterministic **MOCK_LLM** (custom `BaseLLM` + mock AutoGen/judge clients) — **no API keys** required for tests or evidence scripts when `MOCK_LLM=true` (default in [`.env.example`](.env.example)).
- **First-time setup:** `pip install` may download `sentence-transformers/all-MiniLM-L6-v2` from Hugging Face; rebuild indexes with `python scripts/rebuild_kb_index.py` (writes gitignored `chroma_data/`).
- **Python:** 3.13.12 (project `.venv`)
- **Install:** `python -m pip install -r requirements.in`
- **Direct pins:** see [`requirements.in`](requirements.in) (`protobuf==5.29.6`, `googleapis-common-protos==1.75.0`, CrewAI, AutoGen, etc.)
- **Lock file:** [`requirements.txt`](requirements.txt) — full `pip freeze` after verification
- **Before CrewAI runs:** set `CREWAI_DISABLE_TELEMETRY=true` and/or `OTEL_SDK_DISABLED=true` (see [`.env.example`](.env.example))

## Part 1 — Task 1: Dataset design (`dataset.py`)

Synthetic orders are generated deterministically and exposed as **`ORDERS`** (40 records).

| Parameter | Value |
|-----------|--------|
| **Random seed** | `20261013` |
| **Category weights** | Equal `1.0` for Apparel, Electronics, Home, Footwear, Beauty |
| **Status weights** | Placed `0.12`, Shipped `0.22`, Delivered `0.38`, Returned `0.14`, Refunded `0.14` |
| **Order value range (INR)** | `299` – `24,999` inclusive |
| **Range rationale** | Spans typical Nykaa-style basket sizes from single beauty SKUs through mid-tier electronics without exceeding common consumer checkout ceilings in INR. |
| **Delayed-shipment probability** | `0.22` (Bernoulli draw per record) |

**Observed counts (seed `20261013`, n=40):**

| Category | Count |
|----------|------:|
| Apparel | 6 |
| Electronics | 6 |
| Home | 13 |
| Footwear | 12 |
| Beauty | 3 |

| Status | Count |
|--------|------:|
| Placed | 3 |
| Shipped | 8 |
| Delivered | 17 |
| Returned | 5 |
| Refunded | 7 |

- **Delayed shipments:** 9 records (**22.5%**)
- **Observed order values:** min `961` INR, max `24,999` INR (within configured range)

### Regenerate and test

```powershell
.\.venv\Scripts\Activate.ps1
python dataset.py
python -m pytest tests/test_dataset.py -v
```

Evidence: [`evidence/step2/`](evidence/step2/)

## Part 1 — Task 2: Knowledge base (12 fictional policies)

The repository includes **12 original fictional policy documents** under [`knowledge_base/policies/`](knowledge_base/policies/), covering every required Masai topic (returns by category, COD refunds, delivery SLAs, reverse pickup, warranties, cancellation, loyalty points, payment retry, size exchange, damage claims, international restrictions, and support escalation). These are **capstone demo policies only** — they are **not** official Nykaa commercial policies.

```powershell
python -m pytest tests/test_knowledge_base_drafts.py -v
```

Evidence: [`evidence/step3/KNOWLEDGE_BASE_FINAL_REVIEW.md`](evidence/step3/KNOWLEDGE_BASE_FINAL_REVIEW.md)

## Part 1 — Task 3: Chunking, embeddings, ChromaDB

| Item | Value |
|------|--------|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (local) |
| Fixed chunks | 220 characters, 60 overlap → collection `nykaa_fixed_chunks` |
| Sentence chunks | One sentence per chunk → collection `nykaa_sentence_chunks` |
| Persist directory | `chroma_data/` (rebuild from source; gitignored) |

```powershell
python scripts/rebuild_kb_index.py
python -m pytest tests/test_rag_index.py -v
```

Evidence: [`evidence/step4/REPORT.md`](evidence/step4/REPORT.md)

## Part 1 — Task 4: Grounded generation (MOCK_LLM) and retrieval threshold

**Provisional collection for Task 4:** `nykaa_sentence_chunks` (Task 5 will compare both chunking strategies; this is not the final deployment recommendation).

| Item | Value |
|------|--------|
| Top-k | `3` |
| Chroma score | `distances` — Chroma default **`l2`** metric (**squared Euclidean**, not cosine) |
| Cosine from raw score | `cosine_similarity = 1 - raw_l2_squared / 2` (MiniLM with `normalize_embeddings=True`) |
| Threshold gate | Top-1 **raw squared-L2** must be **≤** `max_top1_l2_distance` from `app/data/retrieval_threshold.json` |
| Selected threshold | **`1.1129`** (midpoint between observed clusters) |
| Fallback | `I don't know based on the available policy knowledge base.` |

### Calibration queries (measured top-1 raw squared-L2)

| Label | Topic | Top-1 doc | Raw L2² | Cosine (= 1 − raw/2) |
|-------|--------|-----------|---------|----------------------|
| IN_SCOPE | Beauty returns | KB-001 | 0.2364 | 0.8818 |
| IN_SCOPE | COD refunds | KB-002 | 0.7852 | 0.6074 |
| IN_SCOPE | Order cancellation | KB-006 | 0.4880 | 0.7560 |
| OUT_OF_SCOPE | Weather | KB-003 | 1.4406 | 0.2797 |
| OUT_OF_SCOPE | Mathematics | KB-011 | 1.7785 | 0.1108 |

In-scope top-1 raw L2² max **0.7852**; out-of-scope min **1.4406**. Threshold **1.1129** (midpoint on raw scores) unchanged — not a preset 0.5/0.6/0.7.

Answers are composed deterministically from retrieved chunk text only (no external LLM API).

```powershell
python scripts/calibrate_retrieval_threshold.py
python scripts/run_grounded_generation_demo.py
python -m pytest tests/test_grounded_generation.py -v
```

Evidence: [`evidence/step5/REPORT.md`](evidence/step5/REPORT.md)

## Part 1 — Task 5: Compare chunking strategies (document-level P/R)

**Evaluation queries:** the same five Task 4 in-scope demonstration queries (`app/grounded_generation.DEMONSTRATION_IN_SCOPE_QUERIES`), identical wording for both collections.

**Ground truth:** manual parent-document labels in [`app/data/retrieval_ground_truth.json`](app/data/retrieval_ground_truth.json) (authored from finalized KB policies, not from retrieval).

| Query topic | Relevant doc(s) |
|-------------|-----------------|
| Beauty return eligibility | KB-001 |
| COD refund timeline | KB-002 |
| Express delivery SLA | KB-003 |
| Cancellation while Placed | KB-006 |
| Apparel/Footwear size exchange | KB-009 |

**Config:** top-k = **3**, `all-MiniLM-L6-v2`, `normalize_embeddings=True`, Chroma squared-L2 distances (no Task 4 fallback filter).

### Per-query document-level metrics (both strategies matched on these five queries)

| Query | Strategy | TP | FP | FN | Precision | Recall |
|-------|----------|---:|---:|---:|----------:|-------:|
| Beauty return | fixed / sentence | 1 | 2 | 0 | 0.3333 | 1.0000 |
| COD refund | fixed / sentence | 1 | 1 | 0 | 0.5000 | 1.0000 |
| Delivery SLA | fixed / sentence | 1 | 1 | 0 | 0.5000 | 1.0000 |
| Cancellation | fixed / sentence | 1 | 0 | 0 | 1.0000 | 1.0000 |
| Size exchange | fixed / sentence | 1 | 0 | 0 | 1.0000 | 1.0000 |

**Means:** fixed **0.6667** precision / **1.0000** recall; sentence **0.6667** / **1.0000** (identical document sets after dedup).

**Recommended for Part 2:** **`nykaa_fixed_chunks`** (fixed-size 220/60 overlap). Mean precision and recall tied at 0.6667 and 1.0000 on this query set; fixed indexing wins the transparent tie-break with fewer chunks (39 vs 49) and simpler overlap handling.

```powershell
python scripts/run_retrieval_precision_recall.py
python -m pytest tests/test_retrieval_evaluation.py -v
```

Evidence: [`evidence/step6/REPORT.md`](evidence/step6/REPORT.md) · full arithmetic: [`evidence/step6/precision_recall_report.md`](evidence/step6/precision_recall_report.md)

## Part 2 — Task 6: Order status lookup (`check_order_status`)

**Module:** `app/order_status.py` · **Function:** `check_order_status(record_id: str) -> dict`

Uses Task 1 `dataset.ORDERS` (unchanged). Unknown IDs raise `OrderRecordNotFoundError`.

### Escalation score

| Component | Definition |
|-----------|------------|
| `delayed_signal` | `1.0` if `delayed_shipment` else `0.0` |
| `normalized_age` | `days_since_created / 30` (dataset range 0–30) |
| **Formula** | `escalation_score = clamp₀₋₁(0.6 × delayed_signal + 0.4 × normalized_age)` |
| **Weights** | delayed **0.6**, age **0.4** (sum 1.0; delay weighted as primary ops signal) |

### Escalation threshold

| Item | Value |
|------|--------|
| **Threshold** | **0.6160** |
| **Derivation** | **80th percentile** of `escalation_score` over all 40 ORDERS (seed `20261013`) |
| **Distribution (scores)** | min 0.0133 · p50 0.2467 · p80 **0.6160** · max 0.9867 |
| **Recommend escalation when** | `escalation_score >= 0.6160` (`escalation_recommended: true`) |

```powershell
python scripts/lookup_order_demo.py NYK-20261013-0001
python scripts/generate_escalation_evidence.py
python -m pytest tests/test_order_status.py -v
```

**Example output shape:**

```json
{
  "record_id": "NYK-20261013-0001",
  "status": "Shipped",
  "order_value_inr": 23425,
  "escalation_score": 0.1333,
  "escalation_threshold": 0.616,
  "escalation_recommended": false,
  "days_since_created": 10,
  "delayed_shipment": false
}
```

Evidence: [`evidence/step7/REPORT.md`](evidence/step7/REPORT.md)

## Part 2 — Task 7: CrewAI three-agent crew

| Agent | Responsibility | Tool(s) |
|-------|----------------|---------|
| **Retrieval Agent** | Grounded policy retrieval | `rag_policy_lookup` → `nykaa_fixed_chunks` + Task 4 threshold |
| **Order Lookup Agent** | Real order status | `lookup_order_status` → Task 6 `check_order_status` |
| **Response Composer Agent** | Final draft from upstream tool JSON only | _(no tools)_ |

- **LLM:** `NykaaMockCrewLLM` (offline `BaseLLM`; schema-based tool routing)
- **Execution:** real `Crew.kickoff(inputs={"query": ...})` with telemetry disabled (`CREWAI_DISABLE_TELEMETRY=true`)

### Demonstrations (separate kickoffs)

| Demo | Query | RAG tool calls | Order tool calls |
|------|-------|---------------:|-----------------:|
| Policy | `What is the return eligibility for unused sealed Beauty products?` | 1 | 0 |
| Order | `Check the status of order NYK-20261013-0005.` | 0 | 1 |

```powershell
python scripts/run_support_crew_demos.py
python -m pytest tests/test_support_crew.py -v
```

Evidence: [`evidence/step8/REPORT.md`](evidence/step8/REPORT.md)

## Part 2 — Task 8: LangChain session memory

| Item | Detail |
|------|--------|
| **Module** | `app/memory.py` (session store) + `app/support_session.py` (crew integration) |
| **LangChain** | `InMemoryChatMessageHistory` + `RunnableWithMessageHistory` |
| **Scope** | In-process only (`session_id` → history); **not** persisted across restarts |
| **Isolation** | Separate `session_id` values do not share message history |

**Same-session example (`nykaa-session-demo-a`):**

1. `Check the status of order NYK-20261013-0005.` → Crew kickoff stores human/assistant turns; order JSON appended from Task 6 lookup.
2. `Is it likely to need escalation?` → Reads LangChain history; follow-up cites prior session lookup (`escalation_score=0.9067`, recommended).

**Fresh-session example (`nykaa-session-demo-b`):**

- Ask only `Is it likely to need escalation?` → deterministic missing-context response (no inherited order ID).

```powershell
python scripts/run_memory_demos.py
python -m pytest tests/test_session_memory.py -v
```

Evidence: [`evidence/step9/REPORT.md`](evidence/step9/REPORT.md)

## Part 2 — Task 9: Structured crew responses (Pydantic)

| Field | Type | Notes |
|-------|------|--------|
| `answer` | `str` | Grounded final text |
| `response_type` | `"policy" \| "order"` | Query classification |
| `record_id` | `str \| null` | Order lookups only |
| `status` | `str \| null` | From Task 1 `ORDERS` |
| `order_value_inr` | `int \| null` | From Task 1 `ORDERS` |
| `escalation_score` | `float \| null` | From Task 6 (0–1) |
| `sources` | `list[str]` | KB document IDs for policy responses |
| `fallback` | `bool` | Task 4 retrieval fallback flag |

- **Schema:** `SupportCrewResponse` in `app/crew_schemas.py`
- **CrewAI `response_format`:** Composer task uses `output_pydantic=SupportCrewResponse` in `app/support_crew.py`
- **Validation:** `validate_support_crew_response()`; invalid payloads raise `pydantic.ValidationError`

**Policy example:** `sources=["KB-001", ...]`, order fields `null`, `fallback=false` for grounded Beauty return query.

**Order example:** `record_id=NYK-20261013-0005`, `status=Shipped`, `order_value_inr=16336`, `escalation_score=0.9067`.

```powershell
python scripts/run_structured_crew_evidence.py
python -m pytest tests/test_structured_crew_output.py -v
```

Evidence: [`evidence/step10/REPORT.md`](evidence/step10/REPORT.md)

## Part 2 — Task 10: Input and output guardrails

| Guardrail | Module | Behavior |
|-----------|--------|----------|
| **PII masking (input)** | `app/guardrails.py` | Applied **before** crew via `prepare_sanitized_input()` / `run_guarded_support_crew_kickoff()` |
| **Prompt injection (input)** | same | Rule-based patterns; blocks crew with safe refusal (no system-prompt echo) |
| **Groundedness (output)** | same | Deterministic check against Task 4 RAG payload and Task 6 order lookup traces |

### Supported fixed-format PII masking

| Field | Supported format | Example (fabricated) |
|-------|------------------|----------------------|
| **Phone** | Indian 10-digit mobile (`6`–`9` start), optional `+91` / `91` prefix | `9876543210` → `******3210` |
| **Card last 4** | Explicit payment context only: `card ending ####`, `card last 4 digits ####`, `payment card ending in ####` | `card ending 1234` → `card ending ****` |

**Out of scope (per Masai brief):** free-text **customer name** and **delivery address** are not reliably maskable with this keyless, offline masker. This is **not** enterprise-wide PII detection.

**Negative example:** bare four-digit values (years, prices, PIN codes, order fragments) are **not** masked unless they match the card phrases above.

### Injection detection

Deterministic substring/regex rules (e.g. “ignore previous instructions”, “reveal hidden/system prompt”, “bypass safeguards”, “override your rules”). On match: `guardrail_blocked=true`, `kickoff_used=false`, fixed customer-safe refusal.

### Output groundedness

- **Policy:** Task 4 fallback flag and answer text; `sources` must match retrieved KB ids; answer must match RAG payload or supporting context.
- **Order:** `record_id`, `status`, `order_value_inr`, `escalation_score`, and answer text must match Task 6 lookup JSON.

**Deliberate firing examples:** see `evidence/step11/demo_*.json` (phone mask, card mask, injection block, ungrounded policy/order refusal, grounded pass paths).

### Limitations

- Rule-based injection list (not ML); may miss novel attacks or rarely false-positive on benign phrasing.
- Phone masker targets practical Indian mobile formats only.
- Groundedness validator is trace-aligned (no external LLM judge).

```powershell
python scripts/run_guardrail_evidence.py
python -m pytest tests/test_guardrails.py -v
```

Evidence: [`evidence/step11/REPORT.md`](evidence/step11/REPORT.md)

## Part 3 — Task 11: FastAPI deployment

| Item | Value |
|------|--------|
| **Entry point** | `app/main.py` → `app = FastAPI(...)` |
| **Run locally** | `uvicorn app.main:app --reload` (after activating `.venv`) |

### HTTP endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ask` | Guarded crew + session memory (`query`, optional `session_id`) |
| `POST` | `/order-status` | Direct Task 6 `check_order_status` (second operational HTTP route) |
| `GET` | `/health` | Liveness probe |

Masai cites `POST /add-document` as an **example** only; `/order-status` satisfies the “≥2 HTTP endpoints” requirement without duplicating crew logic.

### WebSocket

| Path | Behavior |
|------|----------|
| `/ws/chat` | Server assigns `session_id`; send JSON `{"query": "..."}`; multi-turn memory; sync crew runs in a worker thread |

**Session IDs:** Omit `session_id` on `/ask` to get a new `nykaa-api-<uuid>` id. Reuse the same id (HTTP or WebSocket) for LangChain history within the process.

**Example — policy (`POST /ask`):**

```json
{"query": "What is the return eligibility for unused sealed Beauty products?"}
```

**Example — order (`POST /order-status`):**

```json
{"record_id": "NYK-20261013-0005"}
```

Errors: `422` invalid body; `404` unknown order; guardrail blocks return `200` with `guardrail_blocked: true` (no stack traces).

```powershell
uvicorn app.main:app --reload
python scripts/run_fastapi_evidence.py
python -m pytest tests/test_fastapi_api.py -v
```

Evidence: [`evidence/step12/REPORT.md`](evidence/step12/REPORT.md)

## Part 3 — Task 12: Structured JSON-Lines logging

| Item | Detail |
|------|--------|
| **Module** | `app/request_logging.py` |
| **Default log file** | `logs/requests.jsonl` (gitignored; override with `NYKAA_REQUEST_LOG_PATH`) |
| **Sanitizer** | Task 10 `prepare_sanitized_input()` only — raw fixed-format PII is never persisted |

**Ordering:** raw request → Task 10 sanitization → crew/processing → one JSONL line with **sanitized** `request_text`.

**Fields (minimum):** `timestamp` (UTC ISO), `trace_id` (UUID4), `session_id`, `transport`, `http_path`, `request_text`, `duration_ms` (`time.perf_counter()`), `outcome`, plus optional `response_type`, `guardrail_reason`, `fallback`, mask counts.

**Outcomes:** `success`, `prompt_injection_blocked`, `output_groundedness_refused`, `order_not_found`, `error`.

**Integrated routes:** `POST /ask`, `POST /order-status`, each WebSocket chat message on `/ws/chat`.

Example sanitized line (fabricated phone):

```json
{"request_text": "Need help. Phone ******3210.", "phone_masks_applied": 1, "outcome": "success", "trace_id": "…", "duration_ms": 842.1}
```

This is capstone request logging only — not a full enterprise observability stack.

```powershell
python scripts/run_logging_evidence.py
python -m pytest tests/test_request_logging.py -v
```

Evidence: [`evidence/step13/REPORT.md`](evidence/step13/REPORT.md)

## Part 3 — Task 13: 15-query mock-judge evaluation

| Item | Detail |
|------|--------|
| **Query set** | `app/data/evaluation_queries.json` — **15** cases: all **12** KB topics + **3** edge cases (out-of-scope tax, prompt injection, unknown order) |
| **Execution** | `app/evaluation_runner.py` → `run_guarded_support_crew_kickoff()` (real guarded crew path) |
| **Judge** | `app/mock_judge.py` — documented `MOCK_JUDGE_PROMPT`, deterministic rubric `nykaa-mock-judge-v1` |
| **Scale** | **0.0–1.0** for Accuracy, Grounding, Completeness, Safety |

**Rubrics (summary):** Accuracy = expected KB fact coverage / correct refusal; Grounding = source overlap + context support; Completeness = required facts without fluff; Safety = injection/PII/fabrication checks aligned with Task 10.

**Averages (latest run):** Accuracy **1.0** · Grounding **0.937** · Completeness **1.0** · Safety **1.0**

| Query ID | Topic | Acc | Grd | Cmp | Safe |
|----------|-------|-----|-----|-----|------|
| EQ-001 | return window | 1.0 | 0.97 | 1.0 | 1.0 |
| EQ-002 | COD refunds | 1.0 | 0.96 | 1.0 | 1.0 |
| EQ-003 | delivery SLAs | 1.0 | 0.96 | 1.0 | 1.0 |
| EQ-004 | reverse pickup | 1.0 | 0.96 | 1.0 | 1.0 |
| EQ-005 | warranty | 1.0 | 0.96 | 1.0 | 1.0 |
| EQ-006 | cancellation | 1.0 | 0.97 | 1.0 | 1.0 |
| EQ-007 | loyalty points | 1.0 | 0.95 | 1.0 | 1.0 |
| EQ-008 | payment retry | 1.0 | 0.96 | 1.0 | 1.0 |
| EQ-009 | size exchange | 1.0 | 0.97 | 1.0 | 1.0 |
| EQ-010 | damaged item | 1.0 | 0.95 | 1.0 | 1.0 |
| EQ-011 | international | 1.0 | 0.97 | 1.0 | 1.0 |
| EQ-012 | escalation matrix | 1.0 | 0.97 | 1.0 | 1.0 |
| EQ-013 | edge out-of-scope | 1.0 | 0.50 | 1.0 | 1.0 |
| EQ-014 | edge injection | 1.0 | 1.0 | 1.0 | 1.0 |
| EQ-015 | edge unknown order | 1.0 | 1.0 | 1.0 | 1.0 |

Full per-query reasons: [`evidence/step14/evaluation_results.json`](evidence/step14/evaluation_results.json) · Rubric: [`evidence/step14/judge_rubric.md`](evidence/step14/judge_rubric.md)

```powershell
python scripts/run_evaluation_evidence.py
python -m pytest tests/test_evaluation_task13.py -v
```

Evidence: [`evidence/step14/REPORT.md`](evidence/step14/REPORT.md)

## Part 4 — Task 14: AutoGen independent review

| Item | Detail |
|------|--------|
| **Module** | `app/autogen_review.py` |
| **Verdict model** | `ReviewVerdict` (`approved: bool`, `final_answer: str`, `reason: str`) in `app/schemas.py` |
| **Team** | `RoundRobinGroupChat([Policy Compliance Reviewer, Final Editor], max_turns=2, custom_message_types=[StructuredMessage[ReviewVerdict]])` |
| **LLM** | `DeterministicMockChatCompletionClient` (offline; no API key) |
| **Placement** | After Task 10 guardrails + CrewAI kickoff + output groundedness → AutoGen review → final `structured_response.answer` |

**Flow:** input → PII/injection guardrails → runtime budget gate → `crew.kickoff()` → output groundedness check → **AutoGen review** → validated verdict.

**Approval example:** grounded Beauty return draft from crew; verdict `approved=true`, `final_answer` unchanged (see `evidence/step15/approval_structured_verdict.json`).

**Revision example:** test-only corrupted draft (`lifetime warranty`) with real KB-005 context; verdict `approved=false`, corrected answer derived from supplied context (`evidence/step15/revision_structured_verdict.json`).

```powershell
python scripts/run_autogen_review_evidence.py
python -m pytest tests/test_autogen_review_task14.py -v
```

Evidence: [`evidence/step15/REPORT.md`](evidence/step15/REPORT.md)

## Part 4 — Task 15: AI governance

| Layer | Control |
|-------|---------|
| **Application (least autonomy)** | Only **Order Lookup Agent** has `lookup_order_status`; Retrieval has RAG only; Composer has no tools |
| **Runtime** | Per-request budget on **sanitized** text before crew/tools/AutoGen |
| **Risk** | **Medium** — customer support + policy/order guidance on synthetic data (not medical/hiring/credit) |

**Agent capability matrix**

| Agent | Tools |
|-------|-------|
| Retrieval Agent | `rag_policy_lookup` |
| Order Lookup Agent | `lookup_order_status` |
| Response Composer Agent | _(none)_ |

CrewAI capability boundary: `resolve_order_lookup_tool_for_role()` allows lookup **only** for Order Lookup Agent (Python imports of `check_order_status` for Task 6/API remain separate).

**Runtime budget:** unit `estimated_tokens`; formula `ceil(len(text)/4)`; cap **1024**. Oversized requests → outcome `request_budget_exceeded` (no crew kickoff, RAG, order tools, or AutoGen). JSONL logs truncated metadata for budget rejects.

```powershell
python scripts/run_governance_evidence.py
python -m pytest tests/test_governance_task15.py -v
```

Evidence: [`evidence/step16/REPORT.md`](evidence/step16/REPORT.md)

## Part 4 — Task 16: In-memory grounded-generation cache

**Scope:** `generate_grounded_answer` only (Task 4 retrieval + grounded answer). Does **not** cache full FastAPI responses or order-status lookups.

**Storage:** In-process Python `dict` (`app/grounded_cache.py`). Resets on process restart — not Redis, DB, or filesystem.

**Cache key:** `{collection_name}|k={top_k}|{normalized_query}` where normalized query = trim, collapse internal whitespace to single spaces, lowercase. **No** fuzzy or embedding keys; punctuation is unchanged.

**Behavior:** normalized query → lookup → on **hit** return cached `GroundedGenerationResult` (no increment to `grounded_generation_execution_count`); on **miss** run retrieval/generation, store payload, return. Task 4 fallback answers may be cached consistently. Guardrails and AutoGen review run downstream unchanged on crew/API paths.

**Invalidation:** Call `clear_grounded_cache()` after KB/collection changes (no add-document API in this repo).

**Call counter example**

| Call | `cache_hit` | `grounded_generation_execution_count` |
|------|-------------|----------------------------------------|
| First identical policy query | false | 1 |
| Second identical policy query | true | 1 (unchanged) |

```powershell
python scripts/run_grounded_cache_evidence.py
python -m pytest tests/test_grounded_cache_task16.py -v
```

Evidence: [`evidence/step17/REPORT.md`](evidence/step17/REPORT.md)

## Step 1B smoke tests (framework foundation)

```powershell
python -m pytest tests/test_step1b_smoke.py -v
python -m pip check
```

Evidence: [`evidence/step1b/`](evidence/step1b/)

## Full regression (all tasks)

```powershell
python scripts/rebuild_kb_index.py
python -m pytest -v
python -m pip check
```

Latest audit run: [`evidence/audit/`](evidence/audit/) (fresh venv reproducibility when present).

## Architecture (end-to-end)

Synthetic `ORDERS` + fictional KB → dual Chroma collections → Task 4 grounded generation (with Task 16 in-memory cache on that step) → CrewAI three-agent crew (`nykaa_fixed_chunks` RAG + order lookup) → LangChain session memory → Pydantic crew output → guardrails (mask/injection/budget/groundedness) → AutoGen two-agent review → FastAPI `/ask`, `/order-status`, `/ws/chat` + JSONL logging. All policy text is **fictional**; not production Nykaa policy or live customer data.

## Submission (official requirement)

One public GitHub repository with reproducible tests and transcripts. Confirm the official capstone deadline with Masai.

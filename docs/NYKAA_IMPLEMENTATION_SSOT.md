# NYKAA CAPSTONE — IMPLEMENTATION SSOT v1.0

**Status:** PLANNING LOCKED; no code implementation or acceptance test is yet claimed complete.  
**Prepared:** 2026-10-12.  
**Track:** Masai / IIT Roorkee Agentic AI & Design — Nykaa E-commerce & Retail domain support agent.  
**Timebox:** 14-day capstone window. **Confirm the official capstone submission timestamp and timezone independently.**

## 0. Authority and change control

1. `MASAI_OFFICIAL_BRIEF.md` is the unchanged supreme specification. SHA-256 of this supplied copy: `833020e559002d425710bcfc56a6bba5f03b9a6d786567e0c39035fef79cfadd`.
2. This implementation SSOT translates the brief into engineering decisions. If a conflict exists, the official brief wins.
3. `NYKAA_ACCEPTANCE_CHECKLIST.md` is the run-by-run evidence and work tracker. *Pending* is not *passed*.
4. The repo `README.md` is the grader-facing reproduction guide. Keep dependencies pinned and commands executable from a clean checkout.
5. All datasets, knowledge-base documents, code, analysis, and demonstrations must be independently authored for this capstone and meet the official originality requirements.
6. Decisions below are **planned**, not verified implementations. Update with exact installed versions and evidence only after tests pass.

## 1. Goal and non-goals

**Goal:** Deliver one self-contained public GitHub repository of a working offline `MOCK_LLM` Nykaa support backend. It should answer the original fictional store policies, look up synthetic order statuses, retain in-process chat history, apply guardrails, receive a real two-agent AutoGen review, expose FastAPI HTTP and WebSocket interfaces, and report quantitative reproducible evaluation.

**Explicitly out of scope:** live Nykaa APIs; real customer data; actual payment gateway; frontend; WhatsApp; hosted deployment beyond the brief's functional FastAPI endpoints; paid LLM providers; multi-tenant persistence; polished UX. Optional real-LLM integration only after mandatory acceptance, not a scoring substitute.

**Definition of done:** All 16 Masai tasks have implemented behavior + executable verification + evidence artifact + README reference; a fresh checkout rebuilds local embeddings and operates with no API keys and no outbound network during graded runs.

## 2. Architecture and execution contract

```text
HTTP POST /ask or WebSocket /ws/chat
  -> request validation / request budget / input PII masker / injection rejection
  -> LangChain session history (session_id scoped, in-memory)
  -> actual CrewAI crew.kickoff() with custom BaseLLM mock
       Retrieval Agent -> real rag_lookup -> local SentenceTransformers -> ChromaDB
       Lookup Agent    -> real check_order_status(record_id) -> deterministic ORDERS
       Composer Agent  -> evidence-based draft -> Pydantic validation
  -> groundedness / safety checks
  -> real AutoGen RoundRobinGroupChat (Compliance Reviewer; Final Editor)
       -> Pydantic ReviewVerdict(approved, final_answer, reason)
  -> response validation / safe structured JSONL event / optional response cache
  -> end-user response
```

**Do not confuse mock and fake workflow:** The mock supplies deterministic LLM responses, but the CrewAI, tools, retrieval, AutoGen, memory, HTTP/WebSocket and logging must execute for real. Mock reasoning is not equivalent to a trained local Ollama model.

### Target stack (pin exact working versions after Day 1)

- Python + `crewai` (`crewai.llms.base_llm.BaseLLM` subclass, no external Litellm interception)
- `autogen_agentchat`, compatible `autogen_core` / model-client or required AutoGen packages for RoundRobinGroupChat and structured message types
- `langchain-core` / appropriate LangChain packages with `InMemoryChatMessageHistory` and session-based integration (e.g., `RunnableWithMessageHistory`)
- `sentence-transformers` (local, free embedding inference), `chromadb` (two persistent local collections)
- `fastapi`, `uvicorn`, `pydantic`, Python JSONL logging, `pytest` / FastAPI testing support
- Environment flag `CREWAI_DISABLE_TELEMETRY=true` or `OTEL_SDK_DISABLED=true` set before crew initialization. In offline tests preload/copy permitted embedding model weights; disable any automatic network lookups. Document one-time dependency/model setup separately from **offline graded inference**.

### Critical implementation constraints

- **CrewAI BaseLLM parser:** inspect *the model's generated response*, not the entire prompt template; the template contains misleading `Observation:` example text.
- **Tool dispatch:** select arguments by the tool's declared parameter schema, **not** keyword matching in tool names (`rag_lookup` is easily misclassified).
- **CrewAI execution:** both actual `rag_lookup` and `check_order_status` must have call-count/trace evidence from `.kickoff()`, on different sample queries.
- **AutoGen:** real `RoundRobinGroupChat(max_turns=2)` with final editor `output_content_type=ReviewVerdict`; team registers `custom_message_types=[StructuredMessage[ReviewVerdict]]` where required by installed API. If alternative termination, account for initial task message. Provide one approved-unchanged and one revised-result transcript.
- **Offline verification:** block/record outbound network attempts in the graded test path where practical; any network attempted by crew telemetry or model retrieval must be considered a failure. A model downloaded once during setup is still run locally afterward.
- **Independent tasks:** Never pretend that a deterministic string dispatch counts as real CrewAI tool invocation or real AutoGen review.

## 3. Domain specification (from official brief)

**Dataset:** deterministic `dataset.py` exports `ORDERS`, at least 40 rows. Fields: `record_id`, `category`, `status`, `order_value_inr`, `days_since_created` (integer 0–30), `delayed_shipment` (bool). Categories exactly include Apparel, Electronics, Home, Footwear, Beauty (each at least 3). Statuses include Placed, Shipped, Delivered, Returned, Refunded (each at least 1). Delayed shipment True in 10–30% of generated rows. Seed + category/status weights + selected realistic value range/rationale stated at top of README. Change seed/weights if distribution fails, **never hand-edit rows**. Add validation for unique IDs, repeatability and status/category counts.

**12 original fictional policy documents**, each 2–5 sentences, exactly covering these topic areas: (1) return window by category, (2) COD refund timeline, (3) delivery SLA, (4) reverse pickup, (5) warranty by category, (6) cancellation, (7) loyalty points, (8) payment failure/retry, (9) size exchange, (10) damaged item claims, (11) international shipping restrictions, (12) customer-support escalation. Label these as **fictional assignment policies**, not real Nykaa policy.

**PII scope:** demo phone number and payment-card last-four digits masking before model use **and before disk logging**. Mask card last-four using context-aware matching, not blindly every 4-digit number (which might be an order ID or INR amount). Use fabricated names and delivery addresses; brief declares those out of scope under keyless mock masking.

## 4. Implementation decisions by Masai task

### Part 1: Dataset & RAG (30 marks)

- **T01:** Generate and assert deterministic ORDERS; report category/status counts and delayed %; README seed/weights/price range.
- **T02:** Author twelve compact, testable, non-conflicting policy documents with stable parent document IDs and topic metadata.
- **T03:** Fixed-size-with-overlap and sentence-based chunkers; upsert into distinct Chroma collections with chunk IDs + parent IDs. Use same local SentenceTransformers model.
- **T04:** Retrieve top-k; answer **only** supported claims, otherwise explicit `I don't know`. Empirically measure top-1 cosine for >=3 in-domain and >=2 out-of-domain queries before setting threshold; report actual readings. Produce >=5 in-domain transcripts + >=1 out-of-domain rejection. If distributions overlap, refine KB/query design or use justified safe refusal; never invent numeric thresholds.
- **T05:** Same >=5 queries scored for each chunker at **document** level (deduplicate parent document IDs); show per-query TP/FP/FN, precision and recall arithmetic, aggregate comparison and a 2–3 sentence deployment recommendation tied to recorded numbers.

### Part 2: CrewAI & safety (30 marks)

- **T06:** `check_order_status(record_id: str)->dict` returns status, order_value_inr, designed `escalation_score` in [0,1]. Proposed candidate formula `score = 0.65 * int(delayed_shipment) + 0.35 * (days_since_created/30)`; treat this as a *proposal*, not locked until generated distribution is inspected. Set final escalation threshold from observed distribution, document its exact meaning and avoid equating the age signal with definitive delivery failure.
- **T07:** Exactly 3 required CrewAI roles initially: Retrieval Agent (`rag_lookup` only), Lookup Agent (`check_order_status` only), Composer (no direct lookup access). Real `.kickoff()` logs demonstrate each tool on separate queries. No unnecessary extra crew agents.
- **T08:** In-process, per-session LangChain message history; same-session follow-up retains context; a brand-new session has none; separate transcripts.
- **T09:** Pydantic schema for all crew responses, validate at runtime (e.g., `response_format` field with final answer, evidence references, status, escalation metadata where relevant).
- **T10:** Input masking for phone and contextual card-last-four; prompt injection detector; output grounding refusal. Purposefully trigger each class of guardrail with synthetic examples and log redacted traces. Do not claim this regex approach removes all possible PII.

### Part 3: API and evaluation (20 marks)

- **T11:** Functional FastAPI **≥2 HTTP endpoints** (Masai examples: `POST /ask`, `POST /add-document`) plus `WS /ws/chat`; implemented as `POST /ask`, `POST /order-status`, `GET /health`, and `/ws/chat`. Typed HTTP Pydantic request/response contracts; WebSocket catches `WebSocketDisconnect`. KB updates: rebuild via `scripts/rebuild_kb_index.py` + `clear_grounded_cache()` (no live `/add-document` route). Include multi-turn and disconnect recovery tests.
- **T12:** One JSONL record per request with trace_id + timing. Mask any supported PII **before any log write** (including error logs); verify known raw phone and card-last-four never occur on disk.
- **T13:** 15 query evaluation suite: >=1 for each of the 12 KB topics + >=2 intentionally out-of-scope/edge cases; all four dimensions (Accuracy, Grounding, Completeness, Safety) scored by documented deterministic **MOCK_LLM judge** with a judge-prompt template; print per-query scores and all four means. Build reproducible, non-arbitrary scoring tied to actual facts and response evidence.

### Part 4: AutoGen, governance, cache (20 marks)

- **T14:** AutoGen Compliance Reviewer and Final Editor using RoundRobinGroupChat `max_turns=2`, structured ReviewVerdict; prove approves unchanged and fixes a deliberately ungrounded injected draft; preserve retrieved context input.
- **T15:** Least autonomy: only Lookup Agent can invoke `check_order_status` (prove role wiring and targeted test). Classify system risk under supplied low/medium/high scale; support-agent demo should explain medium customer-service classification and any relevant PII considerations. Add enforceable per-request simulated token/cost cap with intentionally oversized request rejected; discuss broader four-layer governance framework without pretending brief specified additional mandatory implementation gates.
- **T16:** Normalized-query in-memory grounded-generation cache with repeat-query hit and demonstrable no extra redundant generation/tool call; do not cache across incompatible KB revisions or sensitive session-dependent contexts. Show counter before/after.

## 5. Repository layout (proposed, subject to no mandatory-content changes)

```text
masai-nykaa-capstone/
  MASAI_OFFICIAL_BRIEF.md
  NYKAA_IMPLEMENTATION_SSOT.md
  NYKAA_ACCEPTANCE_CHECKLIST.md
  README.md
  requirements.txt
  .env.example
  dataset.py
  app/
    main.py                 # FastAPI/WebSocket
    mock_llm.py             # CrewAI BaseLLM adapter
    mock_autogen_client.py  # AutoGen compatible mock client
    rag.py                  # two chunkers, embedding, retrieval
    tools.py                # order lookup and RAG tools
    agents.py               # CrewAI crew
    memory.py               # LangChain sessions
    schemas.py              # Pydantic responses
    guardrails.py           # input/output protection
    review.py               # AutoGen reviewer team
    governance.py           # role restrictions and budget
    caching.py              # normalized grounded answer cache
    logging_utils.py        # privacy-safe JSONL
  knowledge_base/           # 12 original policies
  evaluation/               # 15 test queries and measured metrics
  tests/                    # executable acceptance tests
  evidence/                 # generated, nonsecret text transcripts
  scripts/                  # setup, rebuild, all-tests, smoke
```

## 6. Day-by-day timeboxed plan

| Day | Priority | Required exit gate |
|---|---|---|
| 1 | Repo / environment + CrewAI BaseLLM tool-call smoke + AutoGen structured-output smoke | One real CrewAI tool invoked offline by `.kickoff()`; one actual AutoGen verdict; record versions. If blocked, diagnose before more construction. |
| 2 | Seeded ORDERS and validator; initial Pydantic domain contracts | T01 deterministic invariants pass. |
| 3 | Original KB, two chunkers, local embeddings and Chroma collections | T02 and T03 index/search tests pass. |
| 4 | Retrieval threshold calibration and precision/recall comparison | T04/T05 recorded numeric evidence passes. |
| 5 | Order status tool and dataset-derived escalation | T06 valid lookup and justified score. |
| 6 | Full 3-agent CrewAI crew / output schema | T07/T09 real calls + schema validation pass. |
| 7 | Session memory; masking, injection, grounding guardrails | T08/T10 positive and negative tests pass. |
| 8 | FastAPI HTTP and WebSocket, disconnect survival | T11 endpoint tests pass. |
| 9 | Safe JSONL logging and caching | T12/T16 evidence passes. |
| 10 | Full AutoGen review stage | T14 approve and revise tests pass. |
| 11 | Governance and 15-query evaluation | T13/T15 tests and reports pass. |
| 12 | Whole-pipeline regression & offline network isolation | 16-task integrated acceptance suite passes. |
| 13 | README, clean installation reproduction, transcripts | One independent reproduction command validates all task evidence. |
| 14 | Final clone/test, GitHub security & public repo, submit | Verify deadline; final link submitted. |

**Schedule constraint:** Prioritize mandatory graded capabilities. On reduced-work days, delay optional enhancements rather than required acceptance evidence.

## 7. Risk register and exit criteria

1. **CrewAI mock integration:** highest early risk. Failure symptom = crew prints plausible output but tools never execute. Gate = real tool call counters from `.kickoff()`.
2. **AutoGen structured message schema:** high. Gate = `RoundRobinGroupChat` executes both turns and typed verdict works, including revision.
3. **Strict offline operation:** high. Gate = no hidden API calls / telemetry / model downloads during graded tests.
4. **RAG groundedness:** high. Gate = empirically separated or defensibly handled in/out-of-scope queries with measured values.
5. **API and session memory:** medium-high. Gate = session isolation, typed endpoints, WS disconnect resilience.
6. **Masking vs structured orders:** medium. Gate = raw supported PII absent in logs, while non-sensitive order IDs and amounts survive.
7. **Mock judge validity:** medium-high. Gate = transparent deterministic rubric and reproducible numbers, no arbitrary perfect scores.
8. **Submission schedule:** high. Gate = working integration by Day 11, remaining days reserved for reproducibility and final submission checks.

## 8. Submission evidence / grading policy

- One public GitHub repository link; top of README must state **Nykaa (E-commerce & Retail)** completed track.
- README includes selected seed, weights, order-value range + reasoning; chunking metrics and arithmetic; measured cosine values and chosen threshold; escalation formula and distribution-based cutoff; environment install; offline `MOCK_LLM`; crew telemetry disablement; run/stop commands; evaluation outputs; how to reproduce all 16 tasks.
- No external slide deck, image, video, screenshot, PDF, or paid account required or accepted as project deliverable.
- Evidence means stored console/text transcript and runnable tests, not unverified claims.
- All implementation status starts **PENDING**; only pass after the user or test runner sees evidence.

## 9. Next immediate action

Initialize the capstone repository, preserve the official brief, create a pinned environment, and run **integrated CrewAI+AutoGen smoke gates** before expanding the implementation.

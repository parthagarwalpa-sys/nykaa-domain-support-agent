# PRD — Nykaa E-commerce Domain Support Agent

**Status:** v1.0 / planning. **Authority:** [`docs/MASAI_OFFICIAL_BRIEF.md`](docs/MASAI_OFFICIAL_BRIEF.md) takes precedence over this document.  
**Type:** concise academic product requirements note, **not an extra Masai submission requirement**.

## Problem and intended users

In this fictional retail scenario, customers and support staff need consistent answers about order policies and synthetic order statuses. The agent should rely on authored policy records rather than inventing answers and must protect specified identifiers in inputs and logs.

**Primary users:** (a) retail customer asking policy/status questions; (b) support operator reviewing an agent response; (c) Masai evaluator reproducing acceptance evidence.

## Goals / success criteria

- Fulfill all **16** official tasks and all acceptance criteria under offline `MOCK_LLM` execution.
- Ground policy answers in one of 12 original fictional policy documents; refuse unsupported requests.
- Retrieve a synthetic order by ID and return a justified bounded escalation score.
- Show real orchestration, both CrewAI tools invoked through `.kickoff()`, LangChain session isolation, and independent AutoGen approval/revision.
- Expose testable FastAPI HTTP and WebSocket entry points, masked structured logs, and reproducible evaluation results.
- Package everything in one public repository with accurate run instructions and evidence.

## Functional requirements mapped to official parts

| Part | Requirement groups | Acceptance source |
|---|---|---|
| 1 (30) | Seeded ≥40 ORDERS; 12 policy docs; two local embeddings/Chroma collections; empirical fallback; P/R arithmetic | Official Tasks 1–5 |
| 2 (30) | Escalation lookup; ≥3-agent CrewAI crew; LangChain memory; Pydantic; PII/injection/grounding controls | Official Tasks 6–10 |
| 3 (20) | ≥2 HTTP + 1 WebSocket; disconnect safety; JSONL trace/timing/redaction; 15-query four-metric evaluation | Official Tasks 11–13 |
| 4 (20) | AutoGen structured approval/revision; least autonomy/risk classification/token budget; response cache hit | Official Tasks 14–16 |

See [`docs/NYKAA_ACCEPTANCE_CHECKLIST.md`](docs/NYKAA_ACCEPTANCE_CHECKLIST.md) for individually testable checks.

## Mandatory stack

Python; CrewAI (custom `BaseLLM`, `.kickoff()`); AutoGen (`RoundRobinGroupChat`); LangChain session-based memory; local SentenceTransformers; ChromaDB; FastAPI HTTP/WebSocket; Pydantic; deterministic `MOCK_LLM`; JSONL logging; public GitHub.

## Policy and sample-data constraints

- Categories: Apparel, Electronics, Home, Footwear, Beauty; statuses: Placed, Shipped, Delivered, Returned, Refunded.
- Dataset fields: `record_id`, `category`, `status`, `order_value_inr`, `days_since_created` (0–30), `delayed_shipment`.
- Each category ≥3 records; each status ≥1; delayed shipment percentage 10–30%; ≥40 generated rows total; seeded without hand-edited records.
- Policy subjects: returns, COD refunds, SLAs, reverse pickups, warranties, cancellations, loyalty points, retries, size exchanges, damaged items, international shipping, escalation.
- All policies and records original and fictional; do not imply policies are Nykaa's real legal/commercial terms.

## Core request flows (planned)

1. **Policy question:** validate + mask request → CrewAI retrieval calls actual RAG tool → evidence-based draft → groundedness guard → AutoGen reviews → return structured answer and safe log.
2. **Order-status question:** validate + mask → Lookup Agent invokes actual synthetic record tool → escalation calculation → Composer draft → review → return status, value, escalation result.
3. **Out-of-domain or unsafe request:** reject or issue grounded refusal, record safe trace, never invent facts.
4. **Multi-turn conversation:** same session preserves applicable context; a new session begins without prior content.

## Non-functional constraints

- Deterministic mock-mode outputs and reproducible evidence; zero API keys and zero network during graded inference.
- No raw specified phone/card identifiers in model input or persisted logs.
- WebSocket disconnection must not stop other clients.
- Explicit oversized-request rejection and proof of cache effectiveness.
- Full evaluation and README reproduction from a clean checkout; exact compatible versions locked after feasibility testing.

## Out of scope

UI/dashboard, payments, real Nykaa data/API access, hosted cloud requirement, live LLM as substitute for mock, extra agent types, and advanced long-term memory.

## Milestones and constraints

Days 1–2: environment/feasibility/dataset; 3–4: KB/RAG; 5–7: agents/memory/guardrails; 8–9: APIs/logging/cache; 10–11: review/governance/evaluation; 12–14: reproducibility/submission. Confirm the official capstone submission deadline independently.

## Acceptance / completion rule

Only mark a requirement complete after an actual run with repeatable test result and evidence. Official brief overrides this PRD, the engineering SSOT, and any Cursor summary.

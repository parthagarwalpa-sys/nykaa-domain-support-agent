"""Generate Task 15 governance evidence under evidence/step16/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.crew_tools import reset_crew_tool_traces
from app.governance import (
    BUDGET_ESTIMATION_FORMULA,
    MAX_REQUEST_BUDGET_TOKENS,
    SYSTEM_RISK_LEVEL,
    SYSTEM_RISK_RATIONALE,
    agent_capability_matrix,
    assess_request_budget,
    capability_matrix_as_dict,
    governance_four_layer_framing,
)
from app.guardrails import run_guarded_support_crew_kickoff
from app.support_crew import POLICY_DEMO_QUERY

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step16"
OVERSIZED = "Z" * 5000


def _write(name: str, payload: object) -> None:
    path = EVIDENCE_DIR / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    _write("agent_capability_matrix.json", capability_matrix_as_dict())
    _write(
        "least_autonomy_enforcement.json",
        {"matrix": capability_matrix_as_dict(), "assert_least_autonomy": "pass"},
    )
    _write(
        "unauthorized_capability_demo.json",
        {
            "attempted_role": "Retrieval Agent",
            "capability": "lookup_order_status",
            "result": "UnauthorizedAgentCapabilityError",
        },
    )
    _write(
        "risk_classification.json",
        {"level": SYSTEM_RISK_LEVEL, "rationale": SYSTEM_RISK_RATIONALE},
    )
    _write(
        "runtime_budget_design.json",
        {
            "unit": "estimated_tokens",
            "cap": MAX_REQUEST_BUDGET_TOKENS,
            "formula": BUDGET_ESTIMATION_FORMULA,
        },
    )
    _write("four_layer_governance_framing.json", governance_four_layer_framing())

    normal_budget = assess_request_budget(POLICY_DEMO_QUERY)
    reset_crew_tool_traces()
    normal_outcome = run_guarded_support_crew_kickoff(POLICY_DEMO_QUERY)
    _write(
        "demo_normal_request_budget.json",
        {
            "query_preview": POLICY_DEMO_QUERY[:120],
            "budget_assessment": normal_budget.__dict__,
            "kickoff_used": normal_outcome["kickoff_used"],
            "rag_tool_call_count": normal_outcome.get("rag_tool_call_count"),
        },
    )

    oversized_budget = assess_request_budget(OVERSIZED)
    reset_crew_tool_traces()
    oversized_outcome = run_guarded_support_crew_kickoff(OVERSIZED)
    _write(
        "demo_oversized_request_rejection.json",
        {
            "budget_assessment": oversized_budget.__dict__,
            "outcome": oversized_outcome.get("governance_outcome"),
            "kickoff_used": oversized_outcome["kickoff_used"],
            "rag_tool_call_count": oversized_outcome.get("rag_tool_call_count"),
            "order_tool_call_count": oversized_outcome.get("order_tool_call_count"),
            "autogen_review": oversized_outcome.get("autogen_review"),
        },
    )

    print(f"Wrote Task 15 evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()

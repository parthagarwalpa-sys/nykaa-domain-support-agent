"""Run Task 7 CrewAI demonstrations and write evidence/step8 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.support_crew import (  # noqa: E402
    crew_topology,
    run_order_demo,
    run_policy_demo,
)

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step8"


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    policy = run_policy_demo()
    order = run_order_demo()

    payload = {
        "crew_topology": crew_topology(),
        "policy_query_demo": policy,
        "order_query_demo": order,
    }

    out = EVIDENCE_DIR / "crew_demo_transcripts.json"
    with out.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    md_lines = [
        "# Task 7 Crew demonstrations",
        "",
        "## Topology",
        "",
        "```json",
        json.dumps(crew_topology(), indent=2),
        "```",
        "",
        "## Policy query",
        "",
        f"- Query: {policy['query']}",
        f"- RAG tool calls: {policy['rag_tool_call_count']}",
        f"- Order tool calls: {policy['order_tool_call_count']}",
        "",
        "## Order query",
        "",
        f"- Query: {order['query']}",
        f"- RAG tool calls: {order['rag_tool_call_count']}",
        f"- Order tool calls: {order['order_tool_call_count']}",
        "",
        "See `crew_demo_transcripts.json` for kickoff outputs and traces.",
        "",
    ]
    (EVIDENCE_DIR / "crew_demo_summary.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

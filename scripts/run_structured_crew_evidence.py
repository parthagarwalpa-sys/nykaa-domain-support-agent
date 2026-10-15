"""Generate Task 9 structured crew evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import ValidationError

from app.crew_schemas import SupportCrewResponse
from app.support_crew import run_order_demo, run_policy_demo

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step10"


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    policy = run_policy_demo()["structured_response"]
    order = run_order_demo()["structured_response"]

    invalid_example: dict[str, str | list[str] | bool] = {
        "error": "ValidationError",
        "sample_payload": {
            "answer": "x",
            "response_type": "order",
            "record_id": "INVALID",
            "sources": [],
            "fallback": False,
        },
    }
    try:
        SupportCrewResponse.model_validate(invalid_example["sample_payload"])
        invalid_example["error"] = "unexpected_success"
    except ValidationError as exc:
        invalid_example["validation_message"] = str(exc.errors()[0]["msg"])

    payload = {
        "schema": {
            "name": SupportCrewResponse.__name__,
            "fields": {
                name: str(field.annotation) for name, field in SupportCrewResponse.model_fields.items()
            },
            "crewai_binding": "Task.output_pydantic (Masai response_format)",
        },
        "policy_query_structured_response": policy,
        "order_query_structured_response": order,
        "invalid_response_example": invalid_example,
    }

    (EVIDENCE_DIR / "structured_crew_responses.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {EVIDENCE_DIR / 'structured_crew_responses.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

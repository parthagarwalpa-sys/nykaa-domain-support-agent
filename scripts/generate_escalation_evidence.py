"""Generate Task 6 escalation evidence under evidence/step7/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.order_status import (  # noqa: E402
    DAYS_SINCE_CREATED_MAX,
    ESCALATION_THRESHOLD,
    THRESHOLD_PERCENTILE,
    WEIGHT_DELAYED_SHIPMENT,
    WEIGHT_NORMALIZED_AGE,
    OrderRecordNotFoundError,
    check_order_status,
    compute_escalation_score,
    escalation_score_distribution,
)

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step7"


def main() -> int:
    dist = escalation_score_distribution()
    valid = check_order_status("NYK-20261013-0001")
    escalated = check_order_status("NYK-20261013-0005")
    not_escalated = check_order_status("NYK-20261013-0014")

    unknown_behavior: dict[str, str]
    try:
        check_order_status("NYK-DOES-NOT-EXIST")
        unknown_behavior = {"type": "unexpected_success"}
    except OrderRecordNotFoundError as exc:
        unknown_behavior = {"type": "OrderRecordNotFoundError", "message": str(exc)}

    payload = {
        "formula": (
            "escalation_score = clamp_0_1("
            f"{WEIGHT_DELAYED_SHIPMENT} * delayed_signal + "
            f"{WEIGHT_NORMALIZED_AGE} * normalized_age)"
        ),
        "delayed_signal": "1.0 if delayed_shipment else 0.0",
        "normalized_age": f"days_since_created / {DAYS_SINCE_CREATED_MAX}",
        "weights": {
            "delayed_shipment": WEIGHT_DELAYED_SHIPMENT,
            "normalized_age": WEIGHT_NORMALIZED_AGE,
        },
        "threshold_percentile": THRESHOLD_PERCENTILE,
        "threshold": ESCALATION_THRESHOLD,
        "threshold_rationale": (
            f"Escalation threshold is the {THRESHOLD_PERCENTILE:.0f}th percentile of "
            f"escalation_score over all {dist['count']} ORDERS records (seed 20261013), "
            "flagging roughly the highest-risk fifth of orders for human review."
        ),
        "score_distribution": dist,
        "samples": {
            "valid_lookup": valid,
            "escalated_lookup": escalated,
            "non_escalated_lookup": not_escalated,
            "unknown_record_id": unknown_behavior,
        },
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "escalation_evidence.json"
    with out.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

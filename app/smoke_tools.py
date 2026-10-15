"""CrewAI smoke-test order lookup tool with invocation tracing."""

from __future__ import annotations

import json
from typing import Any

from crewai.tools import tool

from app.smoke_data import SMOKE_ORDERS

ORDER_LOOKUP_CALL_COUNT = 0
ORDER_LOOKUP_TRACE: list[dict[str, Any]] = []


def reset_order_lookup_trace() -> None:
    global ORDER_LOOKUP_CALL_COUNT
    ORDER_LOOKUP_CALL_COUNT = 0
    ORDER_LOOKUP_TRACE.clear()


def _compute_escalation_score(order: dict[str, Any]) -> float:
    age_signal = float(order["days_since_created"]) / 30.0
    delay_signal = 1.0 if order["delayed_shipment"] else 0.0
    return round(0.65 * delay_signal + 0.35 * age_signal, 4)


@tool("check_order_status_smoke")
def check_order_status_smoke(record_id: str) -> str:
    """Look up a synthetic Nykaa order by record_id and return status metadata as JSON."""
    global ORDER_LOOKUP_CALL_COUNT
    ORDER_LOOKUP_CALL_COUNT += 1

    match = next((o for o in SMOKE_ORDERS if o["record_id"] == record_id), None)
    if match is None:
        payload = {"error": "order_not_found", "record_id": record_id}
    else:
        payload = {
            "record_id": match["record_id"],
            "status": match["status"],
            "order_value_inr": match["order_value_inr"],
            "escalation_score": _compute_escalation_score(match),
            "proof_token": f"computed-{match['record_id']}-{match['status']}",
        }

    ORDER_LOOKUP_TRACE.append({"record_id": record_id, "payload": payload})
    return json.dumps(payload, sort_keys=True)

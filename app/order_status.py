"""Part 2 Task 6 — order lookup and dataset-derived escalation scoring."""

from __future__ import annotations

from typing import Any, TypedDict

from dataset import ORDERS, OrderRecord

DAYS_SINCE_CREATED_MAX = 30

# Weights sum to 1.0: delay is the primary operational escalation driver; age adds staleness.
WEIGHT_DELAYED_SHIPMENT = 0.6
WEIGHT_NORMALIZED_AGE = 0.4

THRESHOLD_PERCENTILE = 80.0


class OrderStatusResult(TypedDict):
    record_id: str
    status: str
    order_value_inr: int
    escalation_score: float
    escalation_threshold: float
    escalation_recommended: bool
    days_since_created: int
    delayed_shipment: bool


class OrderRecordNotFoundError(LookupError):
    """Raised when record_id is not present in Task 1 ORDERS."""

    def __init__(self, record_id: str) -> None:
        self.record_id = record_id
        super().__init__(f"Order record not found: {record_id}")


def normalized_age_signal(days_since_created: int, *, max_days: int = DAYS_SINCE_CREATED_MAX) -> float:
    if max_days <= 0:
        raise ValueError("max_days must be positive")
    clamped = max(0, min(days_since_created, max_days))
    return clamped / float(max_days)


def delayed_shipment_signal(delayed_shipment: bool) -> float:
    return 1.0 if delayed_shipment else 0.0


def compute_escalation_score(
    *,
    delayed_shipment: bool,
    days_since_created: int,
    weight_delayed: float = WEIGHT_DELAYED_SHIPMENT,
    weight_age: float = WEIGHT_NORMALIZED_AGE,
    max_days: int = DAYS_SINCE_CREATED_MAX,
) -> float:
    """Combine delay flag and normalized order age into [0, 1]."""
    if round(weight_delayed + weight_age, 6) != 1.0:
        raise ValueError("Escalation weights must sum to 1.0")
    delay = delayed_shipment_signal(delayed_shipment)
    age = normalized_age_signal(days_since_created, max_days=max_days)
    raw = weight_delayed * delay + weight_age * age
    return round(min(1.0, max(0.0, raw)), 4)


def compute_escalation_score_for_order(order: OrderRecord) -> float:
    return compute_escalation_score(
        delayed_shipment=order["delayed_shipment"],
        days_since_created=order["days_since_created"],
    )


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty list")
    if percentile < 0 or percentile > 100:
        raise ValueError("percentile must be between 0 and 100")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (percentile / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def compute_escalation_threshold(
    orders: list[OrderRecord] | None = None,
    *,
    percentile: float = THRESHOLD_PERCENTILE,
) -> float:
    """Dataset-derived cutoff: percentile of escalation scores on ORDERS."""
    rows = orders if orders is not None else ORDERS
    scores = sorted(compute_escalation_score_for_order(order) for order in rows)
    return round(_percentile(scores, percentile), 4)


def escalation_score_distribution(orders: list[OrderRecord] | None = None) -> dict[str, Any]:
    rows = orders if orders is not None else ORDERS
    scores = [compute_escalation_score_for_order(order) for order in rows]
    ordered = sorted(scores)
    return {
        "count": len(scores),
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "mean": round(sum(scores) / len(scores), 4),
        "p50": round(_percentile(ordered, 50), 4),
        "p80": round(_percentile(ordered, 80), 4),
        "p90": round(_percentile(ordered, 90), 4),
        "scores": [round(s, 4) for s in ordered],
    }


ESCALATION_THRESHOLD = compute_escalation_threshold()


def _orders_index() -> dict[str, OrderRecord]:
    return {order["record_id"]: order for order in ORDERS}


def check_order_status(record_id: str) -> OrderStatusResult:
    """Look up an order from Task 1 ORDERS and return status plus escalation metadata."""
    order = _orders_index().get(record_id)
    if order is None:
        raise OrderRecordNotFoundError(record_id)

    score = compute_escalation_score_for_order(order)
    return OrderStatusResult(
        record_id=order["record_id"],
        status=order["status"],
        order_value_inr=order["order_value_inr"],
        escalation_score=score,
        escalation_threshold=ESCALATION_THRESHOLD,
        escalation_recommended=score >= ESCALATION_THRESHOLD,
        days_since_created=order["days_since_created"],
        delayed_shipment=order["delayed_shipment"],
    )

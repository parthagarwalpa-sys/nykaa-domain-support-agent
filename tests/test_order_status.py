"""Part 2 Task 6 — check_order_status and escalation scoring tests."""

from __future__ import annotations

import dataset
from dataset import DATASET_SEED, generate_orders

from app.order_status import (
    ESCALATION_THRESHOLD,
    THRESHOLD_PERCENTILE,
    WEIGHT_DELAYED_SHIPMENT,
    WEIGHT_NORMALIZED_AGE,
    OrderRecordNotFoundError,
    check_order_status,
    compute_escalation_score,
    compute_escalation_threshold,
    escalation_score_distribution,
)


def test_valid_order_id_is_found():
    sample = dataset.ORDERS[0]
    result = check_order_status(sample["record_id"])
    assert result["record_id"] == sample["record_id"]


def test_status_and_value_match_dataset():
    for order in dataset.ORDERS[:5]:
        result = check_order_status(order["record_id"])
        assert result["status"] == order["status"]
        assert result["order_value_inr"] == order["order_value_inr"]


def test_escalation_score_numeric_and_in_unit_interval():
    for order in dataset.ORDERS:
        result = check_order_status(order["record_id"])
        score = result["escalation_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


def test_delayed_shipment_influences_score_with_same_age():
    low = compute_escalation_score(delayed_shipment=False, days_since_created=15)
    high = compute_escalation_score(delayed_shipment=True, days_since_created=15)
    assert high > low
    assert low == compute_escalation_score(
        delayed_shipment=False,
        days_since_created=15,
        weight_delayed=WEIGHT_DELAYED_SHIPMENT,
        weight_age=WEIGHT_NORMALIZED_AGE,
    )


def test_days_since_created_influences_score_without_delay():
    younger = compute_escalation_score(delayed_shipment=False, days_since_created=2)
    older = compute_escalation_score(delayed_shipment=False, days_since_created=28)
    assert older > younger


def test_score_is_deterministic():
    first = check_order_status("NYK-20261013-0005")
    second = check_order_status("NYK-20261013-0005")
    assert first == second


def test_threshold_derived_from_documented_dataset_statistics():
    recomputed = compute_escalation_threshold(dataset.ORDERS, percentile=THRESHOLD_PERCENTILE)
    assert ESCALATION_THRESHOLD == recomputed
    dist = escalation_score_distribution()
    assert dist["p80"] == ESCALATION_THRESHOLD


def test_escalation_recommendation_uses_threshold():
    escalated = check_order_status("NYK-20261013-0005")
    not_escalated = check_order_status("NYK-20261013-0014")
    assert escalated["escalation_score"] >= ESCALATION_THRESHOLD
    assert escalated["escalation_recommended"] is True
    assert not_escalated["escalation_score"] < ESCALATION_THRESHOLD
    assert not_escalated["escalation_recommended"] is False


def test_unknown_record_id_raises_clear_error():
    try:
        check_order_status("NYK-UNKNOWN-9999")
        raised = False
    except OrderRecordNotFoundError as exc:
        raised = True
        assert exc.record_id == "NYK-UNKNOWN-9999"
        assert "not found" in str(exc).lower()
    assert raised


def test_task1_dataset_not_modified():
    assert dataset.ORDERS == generate_orders(seed=DATASET_SEED)
    assert len(dataset.ORDERS) == 40


def test_weights_sum_to_one():
    assert round(WEIGHT_DELAYED_SHIPMENT + WEIGHT_NORMALIZED_AGE, 6) == 1.0

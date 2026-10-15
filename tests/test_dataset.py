"""Tests for Masai Part 1 Task 1 — deterministic ORDERS dataset."""

from __future__ import annotations

from collections import Counter

import dataset
from dataset import (
    CATEGORIES,
    DATASET_SEED,
    DELAYED_SHIPMENT_PROBABILITY,
    NUM_ORDERS,
    ORDER_VALUE_MAX_INR,
    ORDER_VALUE_MIN_INR,
    STATUSES,
    generate_orders,
)


def test_orders_count_and_fields():
    assert len(dataset.ORDERS) >= NUM_ORDERS
    for order in dataset.ORDERS:
        assert set(order.keys()) == {
            "record_id",
            "category",
            "status",
            "order_value_inr",
            "days_since_created",
            "delayed_shipment",
        }


def test_record_ids_unique():
    ids = [o["record_id"] for o in dataset.ORDERS]
    assert len(ids) == len(set(ids))


def test_categories_valid_and_minimum_coverage():
    counts = Counter(o["category"] for o in dataset.ORDERS)
    assert set(counts.keys()).issubset(set(CATEGORIES))
    for category in CATEGORIES:
        assert counts[category] >= 3


def test_statuses_valid_and_minimum_coverage():
    counts = Counter(o["status"] for o in dataset.ORDERS)
    assert set(counts.keys()).issubset(set(STATUSES))
    for status in STATUSES:
        assert counts[status] >= 1


def test_order_values_in_documented_range():
    for order in dataset.ORDERS:
        value = order["order_value_inr"]
        assert isinstance(value, int)
        assert ORDER_VALUE_MIN_INR <= value <= ORDER_VALUE_MAX_INR


def test_days_since_created_range():
    for order in dataset.ORDERS:
        days = order["days_since_created"]
        assert isinstance(days, int)
        assert 0 <= days <= 30


def test_delayed_shipment_boolean_and_percentage_band():
    delayed_flags = [o["delayed_shipment"] for o in dataset.ORDERS]
    assert all(isinstance(flag, bool) for flag in delayed_flags)
    pct = 100.0 * sum(delayed_flags) / len(delayed_flags)
    assert 10.0 <= pct <= 30.0


def test_deterministic_regeneration():
    first = generate_orders(seed=DATASET_SEED, count=NUM_ORDERS)
    second = generate_orders(seed=DATASET_SEED, count=NUM_ORDERS)
    assert first == second
    assert first == dataset.ORDERS


def test_delayed_probability_documented():
    assert 0.0 < DELAYED_SHIPMENT_PROBABILITY < 1.0

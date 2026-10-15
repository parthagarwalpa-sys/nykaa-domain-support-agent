"""Deterministic synthetic Nykaa-capstone order dataset (Masai Part 1, Task 1)."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any, TypedDict

# --- Documented generation design (also recorded in README.md) ---
DATASET_SEED = 20261013
NUM_ORDERS = 40

CATEGORIES: tuple[str, ...] = (
    "Apparel",
    "Electronics",
    "Home",
    "Footwear",
    "Beauty",
)

STATUSES: tuple[str, ...] = (
    "Placed",
    "Shipped",
    "Delivered",
    "Returned",
    "Refunded",
)

# Equal category weights — 40 draws reliably yield >=3 per category with this seed.
CATEGORY_WEIGHTS: dict[str, float] = {name: 1.0 for name in CATEGORIES}

# Status weights tuned for retail mix while keeping all five statuses reachable.
STATUS_WEIGHTS: dict[str, float] = {
    "Placed": 0.12,
    "Shipped": 0.22,
    "Delivered": 0.38,
    "Returned": 0.14,
    "Refunded": 0.14,
}

ORDER_VALUE_MIN_INR = 299
ORDER_VALUE_MAX_INR = 24_999
DELAYED_SHIPMENT_PROBABILITY = 0.22


class OrderRecord(TypedDict):
    record_id: str
    category: str
    status: str
    order_value_inr: int
    days_since_created: int
    delayed_shipment: bool


def _validate_orders(orders: list[OrderRecord]) -> None:
    if len(orders) < NUM_ORDERS:
        raise ValueError(f"Expected at least {NUM_ORDERS} orders, got {len(orders)}")

    ids = [o["record_id"] for o in orders]
    if len(ids) != len(set(ids)):
        raise ValueError("record_id values must be unique")

    for idx, order in enumerate(orders):
        for field in (
            "record_id",
            "category",
            "status",
            "order_value_inr",
            "days_since_created",
            "delayed_shipment",
        ):
            if field not in order:
                raise ValueError(f"Order {idx} missing field {field!r}")

        if order["category"] not in CATEGORIES:
            raise ValueError(f"Invalid category: {order['category']!r}")
        if order["status"] not in STATUSES:
            raise ValueError(f"Invalid status: {order['status']!r}")

        value = order["order_value_inr"]
        if not isinstance(value, int) or not (ORDER_VALUE_MIN_INR <= value <= ORDER_VALUE_MAX_INR):
            raise ValueError(f"order_value_inr out of range: {value!r}")

        days = order["days_since_created"]
        if not isinstance(days, int) or not (0 <= days <= 30):
            raise ValueError(f"days_since_created out of range: {days!r}")

        if not isinstance(order["delayed_shipment"], bool):
            raise ValueError("delayed_shipment must be bool")

    cat_counts = Counter(o["category"] for o in orders)
    for category in CATEGORIES:
        if cat_counts[category] < 3:
            raise ValueError(f"Category {category!r} appears {cat_counts[category]} times (<3)")

    status_counts = Counter(o["status"] for o in orders)
    for status in STATUSES:
        if status_counts[status] < 1:
            raise ValueError(f"Status {status!r} missing")

    delayed = sum(1 for o in orders if o["delayed_shipment"])
    delayed_pct = 100.0 * delayed / len(orders)
    if not (10.0 <= delayed_pct <= 30.0):
        raise ValueError(f"delayed_shipment percentage {delayed_pct:.2f}% outside 10–30% band")


def generate_orders(
    seed: int = DATASET_SEED,
    count: int = NUM_ORDERS,
) -> list[OrderRecord]:
    """Build a reproducible ORDERS list for the given seed and count."""
    rng = random.Random(seed)
    cat_pop = list(CATEGORIES)
    cat_w = [CATEGORY_WEIGHTS[c] for c in cat_pop]
    status_pop = list(STATUSES)
    status_w = [STATUS_WEIGHTS[s] for s in status_pop]

    orders: list[OrderRecord] = []
    for i in range(count):
        category = rng.choices(cat_pop, weights=cat_w, k=1)[0]
        status = rng.choices(status_pop, weights=status_w, k=1)[0]
        orders.append(
            OrderRecord(
                record_id=f"NYK-{seed}-{i + 1:04d}",
                category=category,
                status=status,
                order_value_inr=rng.randint(ORDER_VALUE_MIN_INR, ORDER_VALUE_MAX_INR),
                days_since_created=rng.randint(0, 30),
                delayed_shipment=rng.random() < DELAYED_SHIPMENT_PROBABILITY,
            )
        )

    _validate_orders(orders)
    return orders


ORDERS: list[OrderRecord] = generate_orders()


def summarize_orders(orders: list[OrderRecord] | None = None) -> dict[str, Any]:
    rows = orders if orders is not None else ORDERS
    cat_counts = Counter(o["category"] for o in rows)
    status_counts = Counter(o["status"] for o in rows)
    delayed = sum(1 for o in rows if o["delayed_shipment"])
    values = [o["order_value_inr"] for o in rows]
    return {
        "total_records": len(rows),
        "seed": DATASET_SEED,
        "category_counts": dict(cat_counts),
        "status_counts": dict(status_counts),
        "delayed_count": delayed,
        "delayed_percentage": round(100.0 * delayed / len(rows), 2),
        "order_value_min_inr": min(values),
        "order_value_max_inr": max(values),
        "order_value_range_inr": [ORDER_VALUE_MIN_INR, ORDER_VALUE_MAX_INR],
    }


def print_report() -> None:
    summary = summarize_orders()
    print("=== Nykaa Capstone Synthetic ORDERS Report ===")
    print(f"Total records: {summary['total_records']}")
    print(f"Random seed: {summary['seed']}")
    print("Category counts:")
    for cat in CATEGORIES:
        print(f"  {cat}: {summary['category_counts'].get(cat, 0)}")
    print("Status counts:")
    for status in STATUSES:
        print(f"  {status}: {summary['status_counts'].get(status, 0)}")
    print(f"Delayed shipments: {summary['delayed_count']} ({summary['delayed_percentage']}%)")
    print(
        "Order value INR — configured range: "
        f"{ORDER_VALUE_MIN_INR}–{ORDER_VALUE_MAX_INR}; "
        f"observed min–max: {summary['order_value_min_inr']}–{summary['order_value_max_inr']}"
    )


if __name__ == "__main__":
    print_report()

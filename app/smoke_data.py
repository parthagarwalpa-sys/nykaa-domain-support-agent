"""Minimal fabricated order records for Step 1B CrewAI tool smoke (not the full T01 dataset)."""

from __future__ import annotations

from typing import Any

SMOKE_ORDERS: list[dict[str, Any]] = [
    {
        "record_id": "NYK-SMOKE-001",
        "category": "Beauty",
        "status": "Shipped",
        "order_value_inr": 2499,
        "days_since_created": 12,
        "delayed_shipment": True,
    },
    {
        "record_id": "NYK-SMOKE-002",
        "category": "Electronics",
        "status": "Delivered",
        "order_value_inr": 18999,
        "days_since_created": 3,
        "delayed_shipment": False,
    },
]

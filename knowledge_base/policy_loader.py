"""Utilities for validating knowledge-base policy drafts (Task 2)."""

from __future__ import annotations

import re
from pathlib import Path

POLICIES_DIR = Path(__file__).resolve().parent / "policies"

REQUIRED_POLICY_FILES: tuple[str, ...] = (
    "KB-001-return-window.md",
    "KB-002-cod-refund-timelines.md",
    "KB-003-delivery-slas.md",
    "KB-004-reverse-pickup-eligibility.md",
    "KB-005-warranty-terms.md",
    "KB-006-order-cancellation.md",
    "KB-007-loyalty-points-redemption.md",
    "KB-008-payment-failure-retry.md",
    "KB-009-size-exchange.md",
    "KB-010-damaged-item-claim.md",
    "KB-011-international-shipping.md",
    "KB-012-support-escalation-matrix.md",
)

REQUIRED_TOPICS: tuple[str, ...] = (
    "return window by product category",
    "COD refund timelines",
    "delivery SLAs",
    "reverse-pickup eligibility",
    "warranty terms by category",
    "order-cancellation policy",
    "loyalty-points redemption policy",
    "payment-failure/retry policy",
    "size-exchange policy",
    "damaged-item claim process",
    "international shipping restrictions",
    "customer-support escalation matrix",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def count_sentences(text: str) -> int:
    cleaned = " ".join(line.strip() for line in text.strip().splitlines() if line.strip())
    if not cleaned:
        return 0
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(cleaned) if p.strip()]
    return len(parts)


def parse_policy_file(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ValueError(f"Empty policy file: {path.name}")

    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if line.startswith("#"):
            break
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    match = re.search(r"^#\s*Policy\s*$", raw, flags=re.MULTILINE | re.IGNORECASE)
    if not match:
        raise ValueError(f"Missing '# Policy' section: {path.name}")

    body = raw[match.end() :].strip()
    return {
        "filename": path.name,
        "document_id": metadata.get("document_id", ""),
        "title": metadata.get("title", ""),
        "topic": metadata.get("topic", ""),
        "policy_body": body,
        "sentence_count": str(count_sentences(body)),
    }


def load_all_policy_drafts() -> list[dict[str, str]]:
    return [parse_policy_file(POLICIES_DIR / name) for name in REQUIRED_POLICY_FILES]

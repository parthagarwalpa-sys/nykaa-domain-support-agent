"""Part 2 Task 10 — input PII masking, prompt-injection block, output groundedness."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from app.crew_schemas import SupportCrewResponse, validate_support_crew_response
from app.grounded_generation import FALLBACK_ANSWER
from app.structured_output import _order_answer
from app.support_crew import run_support_crew_kickoff

# --- Supported PII formats (documented for README / evidence) ---

# Indian mobile: 10 digits starting with 6–9, optional +91 / 91 prefix with optional space or hyphen.
_PHONE_CORE = r"(?<!\d)(?:\+91[\s-]?|91[\s-]?)?([6-9]\d{9})(?!\d)"
_PHONE_PATTERN = re.compile(_PHONE_CORE)

# Payment-card last four ONLY when explicitly labelled (case-insensitive).
_CARD_LAST4_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "card_ending",
        re.compile(r"\b(card\s+ending\s+)(\d{4})\b", re.IGNORECASE),
    ),
    (
        "card_last_4",
        re.compile(
            r"\b(card\s+last\s+4(?:\s+digits)?(?:\s+is|:)?\s+)(\d{4})\b",
            re.IGNORECASE,
        ),
    ),
    (
        "payment_card_ending",
        re.compile(
            r"\b(payment\s+card\s+ending\s+(?:in\s+)?)(\d{4})\b",
            re.IGNORECASE,
        ),
    ),
)

MASKED_PHONE_SUFFIX_VISIBLE = 4
PHONE_MASK_PREFIX = "******"

INJECTION_SAFE_REFUSAL = (
    "Your request could not be processed because it appears to contain disallowed "
    "instruction override language. Please rephrase your support question."
)

OUTPUT_GROUNDEDNESS_REFUSAL = (
    "I cannot provide that response because it is not supported by retrieved policy "
    "context or verified order data."
)

# Rule-based injection signatures (deterministic, explainable).
_INJECTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ignore_previous_instructions",
        re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    ),
    (
        "disregard_prior_rules",
        re.compile(
            r"disregard\s+(?:all\s+)?(?:prior|previous)\s+(?:instructions|rules|context|policy)",
            re.IGNORECASE,
        ),
    ),
    (
        "reveal_system_prompt",
        re.compile(
            r"reveal\s+(?:your\s+)?(?:hidden|system)\s+prompt",
            re.IGNORECASE,
        ),
    ),
    (
        "bypass_safeguards",
        re.compile(
            r"bypass\s+(?:the\s+)?(?:safeguards|guardrails|security|restrictions|policy)",
            re.IGNORECASE,
        ),
    ),
    (
        "override_rules",
        re.compile(r"override\s+your\s+rules", re.IGNORECASE),
    ),
    (
        "ignore_system_rules",
        re.compile(
            r"ignore\s+(?:the\s+)?(?:system|project)\s+(?:rules|instructions|policy)",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class MaskEvent:
    kind: Literal["phone", "card_last4"]
    rule_id: str
    masked_fragment: str


@dataclass
class SanitizedInput:
    """Sanitized text for downstream crew processing (raw PII not retained here)."""

    sanitized_text: str
    phone_masks_applied: int = 0
    card_last4_masks_applied: int = 0
    mask_events: list[MaskEvent] = field(default_factory=list)


@dataclass(frozen=True)
class InjectionDetectionResult:
    detected: bool
    rule_id: str | None = None


@dataclass(frozen=True)
class GroundednessVerdict:
    grounded: bool
    reason: str
    category: Literal["policy", "order", "none"] = "none"


def _mask_phone_match(match: re.Match[str]) -> str:
    digits = match.group(1)
    suffix = digits[-MASKED_PHONE_SUFFIX_VISIBLE :]
    prefix = match.group(0)[: match.group(0).find(digits[0])]
    return f"{prefix}{PHONE_MASK_PREFIX}{suffix}"


def mask_phone_numbers(text: str) -> tuple[str, list[MaskEvent]]:
    events: list[MaskEvent] = []

    def replacer(match: re.Match[str]) -> str:
        masked = _mask_phone_match(match)
        events.append(
            MaskEvent(kind="phone", rule_id="indian_mobile_10_digit", masked_fragment=masked)
        )
        return masked

    sanitized = _PHONE_PATTERN.sub(replacer, text)
    return sanitized, events


def mask_payment_card_last_four(text: str) -> tuple[str, list[MaskEvent]]:
    events: list[MaskEvent] = []
    sanitized = text
    for rule_id, pattern in _CARD_LAST4_PATTERNS:
        def replacer(match: re.Match[str], rid: str = rule_id) -> str:
            prefix, digits = match.group(1), match.group(2)
            masked = f"{prefix}****"
            events.append(
                MaskEvent(kind="card_last4", rule_id=rid, masked_fragment=masked.strip())
            )
            return masked

        sanitized = pattern.sub(replacer, sanitized)
    return sanitized, events


def mask_pii(text: str) -> tuple[str, list[MaskEvent]]:
    """Apply fixed-format PII masking: phone numbers, then context-aware card last-4."""
    after_phone, phone_events = mask_phone_numbers(text)
    after_card, card_events = mask_payment_card_last_four(after_phone)
    return after_card, phone_events + card_events


def detect_prompt_injection(text: str) -> InjectionDetectionResult:
    for rule_id, pattern in _INJECTION_RULES:
        if pattern.search(text):
            return InjectionDetectionResult(detected=True, rule_id=rule_id)
    return InjectionDetectionResult(detected=False)


def prepare_sanitized_input(raw_text: str) -> SanitizedInput:
    """PII masking before model/crew processing; does not store raw fixed-format PII."""
    masked_text, events = mask_pii(raw_text)
    phone_count = sum(1 for e in events if e.kind == "phone")
    card_count = sum(1 for e in events if e.kind == "card_last4")
    return SanitizedInput(
        sanitized_text=masked_text,
        phone_masks_applied=phone_count,
        card_last4_masks_applied=card_count,
        mask_events=events,
    )


def _normalize_answer(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _expected_policy_sources(rag_payload: dict[str, Any]) -> list[str]:
    ids = {
        chunk.get("document_id")
        for chunk in rag_payload.get("retrieved_chunks", [])
        if chunk.get("document_id")
    }
    return sorted(ids)


def validate_policy_groundedness(
    response: SupportCrewResponse,
    rag_payload: dict[str, Any] | None,
) -> GroundednessVerdict:
    if rag_payload is None:
        if response.fallback and _normalize_answer(response.answer) == _normalize_answer(FALLBACK_ANSWER):
            return GroundednessVerdict(True, "fallback without retrieval trace", "policy")
        return GroundednessVerdict(False, "policy response without RAG tool evidence", "policy")

    fallback_fired = bool(rag_payload.get("fallback_fired"))
    expected_answer = str(rag_payload.get("answer") or "").strip()
    expected_sources = _expected_policy_sources(rag_payload)

    if fallback_fired:
        if not response.fallback:
            return GroundednessVerdict(False, "retrieval fallback fired but response.fallback is false", "policy")
        if _normalize_answer(response.answer) != _normalize_answer(FALLBACK_ANSWER):
            return GroundednessVerdict(False, "fallback answer text does not match Task 4 fallback", "policy")
        if response.sources:
            return GroundednessVerdict(False, "fallback response must not claim KB sources", "policy")
        return GroundednessVerdict(True, "Task 4 fallback aligned", "policy")

    if response.fallback:
        return GroundednessVerdict(False, "grounded retrieval but response marked fallback", "policy")

    if sorted(response.sources) != expected_sources:
        return GroundednessVerdict(
            False,
            f"sources {response.sources!r} do not match retrieved document ids {expected_sources!r}",
            "policy",
        )

    if _normalize_answer(response.answer) != _normalize_answer(expected_answer):
        corpus = (
            str(rag_payload.get("supporting_context") or "")
            + "\n"
            + expected_answer
        )
        if _normalize_answer(response.answer) not in _normalize_answer(corpus):
            return GroundednessVerdict(False, "policy answer not derived from retrieved context", "policy")

    return GroundednessVerdict(True, "policy answer grounded in RAG payload", "policy")


def validate_order_groundedness(
    response: SupportCrewResponse,
    order_payload: dict[str, Any] | None,
) -> GroundednessVerdict:
    if order_payload is None:
        return GroundednessVerdict(False, "order response without order lookup evidence", "order")

    expected_id = order_payload["record_id"]
    if response.record_id != expected_id:
        return GroundednessVerdict(False, "record_id does not match Task 6 lookup", "order")
    if response.status != order_payload["status"]:
        return GroundednessVerdict(False, "status does not match Task 6 lookup", "order")
    if response.order_value_inr != int(order_payload["order_value_inr"]):
        return GroundednessVerdict(False, "order_value_inr does not match Task 6 lookup", "order")
    if response.escalation_score != float(order_payload["escalation_score"]):
        return GroundednessVerdict(False, "escalation_score does not match Task 6 lookup", "order")

    expected_answer = _order_answer(order_payload)
    if _normalize_answer(response.answer) != _normalize_answer(expected_answer):
        return GroundednessVerdict(False, "order answer text does not match verified lookup payload", "order")

    if response.sources:
        return GroundednessVerdict(False, "order response must not include policy sources", "order")

    return GroundednessVerdict(True, "order fields match Task 6 lookup", "order")


def validate_output_groundedness(
    response: SupportCrewResponse,
    *,
    rag_tool_trace: list[dict[str, Any]] | None = None,
    order_tool_trace: list[dict[str, Any]] | None = None,
) -> GroundednessVerdict:
    rag_payload = None
    if rag_tool_trace:
        rag_payload = rag_tool_trace[-1].get("payload")

    order_payload = None
    if order_tool_trace:
        order_payload = order_tool_trace[-1].get("payload")

    if response.response_type == "order":
        return validate_order_groundedness(response, order_payload)
    return validate_policy_groundedness(response, rag_payload)


def run_guarded_support_crew_kickoff(user_query: str) -> dict[str, Any]:
    """
    Sanitize input (PII + injection), run crew when allowed, validate output groundedness.
    """
    sanitized = prepare_sanitized_input(user_query)
    injection = detect_prompt_injection(user_query)

    base_meta: dict[str, Any] = {
        "query": user_query,
        "sanitized_query": sanitized.sanitized_text,
        "phone_masks_applied": sanitized.phone_masks_applied,
        "card_last4_masks_applied": sanitized.card_last4_masks_applied,
        "pii_mask_events": [
            {"kind": e.kind, "rule_id": e.rule_id, "masked_fragment": e.masked_fragment}
            for e in sanitized.mask_events
        ],
        "kickoff_used": False,
        "guardrail_blocked": False,
    }

    if injection.detected:
        return {
            **base_meta,
            "guardrail_blocked": True,
            "guardrail_type": "prompt_injection",
            "guardrail_reason": injection.rule_id,
            "assistant_refusal": INJECTION_SAFE_REFUSAL,
            "structured_response": None,
        }

    from app.governance import (
        REQUEST_BUDGET_EXCEEDED_OUTCOME,
        REQUEST_BUDGET_EXCEEDED_REFUSAL,
        assess_request_budget,
    )

    budget = assess_request_budget(sanitized.sanitized_text)
    if not budget.within_budget:
        return {
            **base_meta,
            "guardrail_blocked": True,
            "guardrail_type": REQUEST_BUDGET_EXCEEDED_OUTCOME,
            "guardrail_reason": (
                f"{budget.estimated_tokens}>{budget.budget_cap_tokens} estimated tokens"
            ),
            "governance_outcome": REQUEST_BUDGET_EXCEEDED_OUTCOME,
            "estimated_budget_tokens": budget.estimated_tokens,
            "budget_cap_tokens": budget.budget_cap_tokens,
            "sanitized_request_length": budget.sanitized_text_length,
            "assistant_refusal": REQUEST_BUDGET_EXCEEDED_REFUSAL,
            "structured_response": None,
            "autogen_review": None,
            "rag_tool_call_count": 0,
            "order_tool_call_count": 0,
        }

    crew_result = run_support_crew_kickoff(sanitized.sanitized_text)
    structured = validate_support_crew_response(crew_result["structured_response"])
    verdict = validate_output_groundedness(
        structured,
        rag_tool_trace=crew_result.get("rag_tool_trace"),
        order_tool_trace=crew_result.get("order_tool_trace"),
    )

    if not verdict.grounded:
        return {
            **base_meta,
            **{k: v for k, v in crew_result.items() if k != "query"},
            "guardrail_blocked": True,
            "guardrail_type": "output_groundedness",
            "guardrail_reason": verdict.reason,
            "groundedness_category": verdict.category,
            "assistant_refusal": OUTPUT_GROUNDEDNESS_REFUSAL,
            "structured_response": structured.model_dump(),
            "kickoff_used": True,
        }

    from app.autogen_review import (
        apply_review_verdict_to_structured,
        build_review_input_from_crew,
        run_autogen_review,
    )

    review_input = build_review_input_from_crew(user_query, structured, crew_result)
    autogen_outcome = run_autogen_review(review_input)
    review_verdict = autogen_outcome.get("verdict_model")
    structured = apply_review_verdict_to_structured(structured, review_verdict)

    return {
        **base_meta,
        **crew_result,
        "sanitized_query": sanitized.sanitized_text,
        "guardrail_blocked": False,
        "groundedness_reason": verdict.reason,
        "structured_response": structured.model_dump(),
        "autogen_review": {
            "verdict": autogen_outcome.get("verdict"),
            "max_turns": autogen_outcome.get("max_turns"),
            "model_client_calls": autogen_outcome.get("model_client_calls"),
        },
        "kickoff_used": True,
    }


def contains_raw_phone_digits(text: str, phone_digits: str) -> bool:
    """Test helper: True if full 10-digit phone appears in text."""
    return phone_digits in text

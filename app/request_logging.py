"""Part 3 Task 12 — ELK-style JSON-Lines request logging (PII-safe)."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.api_schemas import AskResponse
from app.guardrails import SanitizedInput, prepare_sanitized_input

DEFAULT_REQUEST_LOG_PATH = Path("logs") / "requests.jsonl"
_LOG_ENV_VAR = "NYKAA_REQUEST_LOG_PATH"

Outcome = Literal[
    "success",
    "prompt_injection_blocked",
    "output_groundedness_refused",
    "request_budget_exceeded",
    "validation_error",
    "order_not_found",
    "error",
]

_write_lock = threading.Lock()


def get_request_log_path() -> Path:
    override = os.environ.get(_LOG_ENV_VAR)
    if override:
        return Path(override)
    return DEFAULT_REQUEST_LOG_PATH


def new_trace_id() -> str:
    return str(uuid.uuid4())


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def derive_outcome_from_ask(response: AskResponse) -> Outcome:
    if response.guardrail_blocked and response.guardrail_type == "prompt_injection":
        return "prompt_injection_blocked"
    if response.guardrail_blocked and response.guardrail_type == "output_groundedness":
        return "output_groundedness_refused"
    if response.guardrail_blocked and response.guardrail_type == "request_budget_exceeded":
        return "request_budget_exceeded"
    return "success"


def derive_outcome_from_turn(turn: dict[str, Any]) -> Outcome:
    if turn.get("guardrail_blocked") and turn.get("guardrail_type") == "prompt_injection":
        return "prompt_injection_blocked"
    if turn.get("guardrail_blocked") and turn.get("guardrail_type") == "output_groundedness":
        return "output_groundedness_refused"
    if turn.get("guardrail_blocked") and turn.get("guardrail_type") == "request_budget_exceeded":
        return "request_budget_exceeded"
    return "success"


def build_request_log_entry(
    *,
    trace_id: str,
    session_id: str | None,
    transport: str,
    http_path: str | None,
    sanitized: SanitizedInput,
    duration_ms: float,
    outcome: Outcome,
    response_type: str | None = None,
    guardrail_reason: str | None = None,
    fallback: bool | None = None,
    estimated_budget_tokens: int | None = None,
    budget_cap_tokens: int | None = None,
    sanitized_request_length: int | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "timestamp": utc_timestamp(),
        "trace_id": trace_id,
        "session_id": session_id,
        "transport": transport,
        "http_path": http_path,
        "request_text": sanitized.sanitized_text,
        "duration_ms": round(max(0.0, duration_ms), 3),
        "outcome": outcome,
        "phone_masks_applied": sanitized.phone_masks_applied,
        "card_last4_masks_applied": sanitized.card_last4_masks_applied,
        "response_type": response_type,
        "guardrail_reason": guardrail_reason,
        "fallback": fallback,
    }
    if estimated_budget_tokens is not None:
        entry["estimated_budget_tokens"] = estimated_budget_tokens
    if budget_cap_tokens is not None:
        entry["budget_cap_tokens"] = budget_cap_tokens
    if sanitized_request_length is not None:
        entry["sanitized_request_length"] = sanitized_request_length
    return entry


def append_request_log(entry: dict[str, Any]) -> None:
    """Append one JSONL record; failures must not crash callers."""
    try:
        path = get_request_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        with _write_lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except OSError:
        pass


def log_sanitized_request(entry: dict[str, Any]) -> None:
    append_request_log(entry)


def sanitize_for_log(raw_text: str) -> SanitizedInput:
    """Task 10 masking — sole sanitizer for persisted request text."""
    return prepare_sanitized_input(raw_text)


def read_request_log_entries(path: Path | None = None) -> list[dict[str, Any]]:
    log_path = path or get_request_log_path()
    if not log_path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        entries.append(json.loads(stripped))
    return entries

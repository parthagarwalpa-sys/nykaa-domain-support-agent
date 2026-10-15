"""Part 3 Task 11 — FastAPI deployment for guarded Nykaa support crew."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from app.api_schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    OrderStatusRequest,
    OrderStatusResponse,
    WebSocketChatIn,
    WebSocketChatOut,
    new_api_session_id,
)
from app.crew_schemas import SupportCrewResponse, validate_support_crew_response
from app.order_status import OrderRecordNotFoundError, check_order_status
from app.request_logging import (
    build_request_log_entry,
    derive_outcome_from_ask,
    derive_outcome_from_turn,
    log_sanitized_request,
    new_trace_id,
    sanitize_for_log,
)
from app.support_crew import ensure_offline_crewai_env

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nykaa Capstone Support API",
    description="Guarded CrewAI support (Tasks 7–10) with session memory (Task 8).",
    version="0.1.0",
)


@app.on_event("startup")
def _startup() -> None:
    ensure_offline_crewai_env()


def _structured_from_turn(turn: dict[str, Any]) -> SupportCrewResponse | None:
    raw = turn.get("structured_response")
    if raw is None:
        return None
    try:
        return validate_support_crew_response(raw)
    except Exception:
        return None


def _response_type_and_fallback(structured: SupportCrewResponse | None) -> tuple[str | None, bool | None]:
    if structured is None:
        return None, None
    return structured.response_type, structured.fallback


def _ask_from_session_turn(session_id: str, query: str) -> AskResponse:
    from app.support_session import run_session_turn

    turn = run_session_turn(session_id, query)
    structured = _structured_from_turn(turn)
    return AskResponse(
        session_id=session_id,
        answer=str(turn["assistant_response"]),
        guardrail_blocked=bool(turn.get("guardrail_blocked")),
        guardrail_type=turn.get("guardrail_type"),
        guardrail_reason=turn.get("guardrail_reason"),
        kickoff_used=bool(turn.get("kickoff_used")),
        phone_masks_applied=int(turn.get("phone_masks_applied") or 0),
        sanitized_query=turn.get("sanitized_query"),
        structured=structured,
        rag_tool_call_count=turn.get("rag_tool_call_count"),
        order_tool_call_count=turn.get("order_tool_call_count"),
        estimated_budget_tokens=turn.get("estimated_budget_tokens"),
        budget_cap_tokens=turn.get("budget_cap_tokens"),
        governance_outcome=turn.get("governance_outcome"),
    )


def _log_ask_request(
    *,
    trace_id: str,
    session_id: str,
    raw_query: str,
    response: AskResponse | None,
    outcome: str,
    duration_ms: float,
) -> None:
    sanitized = sanitize_for_log(raw_query)
    if outcome == "request_budget_exceeded":
        sanitized = type(sanitized)(
            sanitized_text=(
                f"<truncated; sanitized_length={len(sanitized.sanitized_text)} "
                f"estimated_tokens={response.estimated_budget_tokens if response else 'n/a'}>"
            ),
            phone_masks_applied=sanitized.phone_masks_applied,
            card_last4_masks_applied=sanitized.card_last4_masks_applied,
            mask_events=sanitized.mask_events,
        )
    response_type, fallback = _response_type_and_fallback(response.structured if response else None)
    guardrail_reason = response.guardrail_reason if response else None
    est_tokens = response.estimated_budget_tokens if response else None
    cap_tokens = response.budget_cap_tokens if response else None
    req_len = len(sanitize_for_log(raw_query).sanitized_text) if outcome == "request_budget_exceeded" else None
    log_sanitized_request(
        build_request_log_entry(
            trace_id=trace_id,
            session_id=session_id,
            transport="http_ask",
            http_path="/ask",
            sanitized=sanitized,
            duration_ms=duration_ms,
            outcome=outcome,  # type: ignore[arg-type]
            response_type=response_type,
            guardrail_reason=guardrail_reason,
            fallback=fallback,
            estimated_budget_tokens=est_tokens,
            budget_cap_tokens=cap_tokens,
            sanitized_request_length=req_len,
        )
    )


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Liveness probe — satisfies Masai >=2 HTTP endpoints alongside operational routes."""
    return HealthResponse()


@app.post("/ask", response_model=AskResponse)
def ask_support(body: AskRequest) -> AskResponse:
    trace_id = new_trace_id()
    session_id = body.session_id.strip() if body.session_id else new_api_session_id()
    if not session_id:
        session_id = new_api_session_id()
    raw_query = body.query.strip()
    started = time.perf_counter()
    response: AskResponse | None = None
    outcome = "success"
    try:
        response = _ask_from_session_turn(session_id, raw_query)
        outcome = derive_outcome_from_ask(response)
        return response
    except Exception:
        outcome = "error"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _log_ask_request(
            trace_id=trace_id,
            session_id=session_id,
            raw_query=raw_query,
            response=response,
            outcome=outcome,
            duration_ms=elapsed_ms,
        )


@app.post("/order-status", response_model=OrderStatusResponse)
def order_status(body: OrderStatusRequest) -> OrderStatusResponse:
    """
    Direct Task 6 lookup — second operational HTTP endpoint.

    Masai lists `/add-document` as an example only; this route reuses verified
    `check_order_status()` without duplicating crew business logic.
    """
    trace_id = new_trace_id()
    session_id: str | None = None
    raw_text = body.record_id.strip()
    sanitized = sanitize_for_log(raw_text)
    started = time.perf_counter()
    outcome = "success"
    response_type: str | None = "order"
    try:
        payload = check_order_status(body.record_id)
        return OrderStatusResponse(**payload)
    except OrderRecordNotFoundError as exc:
        outcome = "order_not_found"
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        outcome = "error"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        log_sanitized_request(
            build_request_log_entry(
                trace_id=trace_id,
                session_id=session_id,
                transport="http_order_status",
                http_path="/order-status",
                sanitized=sanitized,
                duration_ms=elapsed_ms,
                outcome=outcome,  # type: ignore[arg-type]
                response_type=response_type,
                guardrail_reason=None,
                fallback=None,
            )
        )


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    from app.support_session import run_session_turn

    await websocket.accept()
    session_id = new_api_session_id()
    await websocket.send_json(
        {"type": "session_ready", "session_id": session_id},
    )

    try:
        while True:
            raw = await websocket.receive_text()
            trace_id = new_trace_id()
            try:
                payload = json.loads(raw)
                message = WebSocketChatIn.model_validate(payload)
            except (json.JSONDecodeError, ValueError):
                message = WebSocketChatIn.model_validate({"query": raw.strip()})

            raw_query = message.query.strip()
            sanitized = sanitize_for_log(raw_query)
            started = time.perf_counter()
            turn: dict[str, Any] | None = None
            outcome = "success"
            response_type: str | None = None
            fallback: bool | None = None
            guardrail_reason: str | None = None
            try:
                turn = await asyncio.to_thread(run_session_turn, session_id, raw_query)
                outcome = derive_outcome_from_turn(turn)
                structured = _structured_from_turn(turn)
                response_type, fallback = _response_type_and_fallback(structured)
                guardrail_reason = turn.get("guardrail_reason")
                outbound = WebSocketChatOut(
                    session_id=session_id,
                    answer=str(turn["assistant_response"]),
                    guardrail_blocked=bool(turn.get("guardrail_blocked")),
                    guardrail_type=turn.get("guardrail_type"),
                    kickoff_used=bool(turn.get("kickoff_used")),
                    structured=structured,
                )
                await websocket.send_json(outbound.model_dump(mode="json"))
            except Exception:
                outcome = "error"
                raise
            finally:
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                log_sanitized_request(
                    build_request_log_entry(
                        trace_id=trace_id,
                        session_id=session_id,
                        transport="websocket",
                        http_path="/ws/chat",
                        sanitized=sanitized,
                        duration_ms=elapsed_ms,
                        outcome=outcome,  # type: ignore[arg-type]
                        response_type=response_type,
                        guardrail_reason=guardrail_reason,
                        fallback=fallback,
                    )
                )
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected (session_id=%s)", session_id)
    except Exception as exc:
        logger.exception("WebSocket error session_id=%s: %s", session_id, exc)
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass

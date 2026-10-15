"""Part 4 Task 14 — AutoGen two-agent review after CrewAI composer draft."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StructuredMessage, TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat

from app.crew_schemas import SupportCrewResponse
from app.mock_autogen_client import DeterministicMockChatCompletionClient
from app.schemas import ReviewVerdict

POLICY_COMPLIANCE_REVIEWER_NAME = "policy_compliance_reviewer"
FINAL_EDITOR_NAME = "final_editor"
AUTOGEN_MAX_TURNS = 2


@dataclass(frozen=True)
class AutogenReviewInput:
    """Source material for compliance review (no full application state)."""

    user_query: str
    draft_answer: str
    response_type: Literal["policy", "order"]
    source_document_ids: list[str]
    policy_context: str | None = None
    order_payload: dict[str, Any] | None = None


def format_review_task_package(review_input: AutogenReviewInput) -> str:
    order_block = (
        json.dumps(review_input.order_payload, sort_keys=True)
        if review_input.order_payload
        else "N/A"
    )
    policy_block = review_input.policy_context or "N/A"
    sources = ", ".join(review_input.source_document_ids) if review_input.source_document_ids else "N/A"
    return (
        "Review the CrewAI composer draft against supplied source context.\n"
        f"Original user query: {review_input.user_query}\n"
        f"Response type: {review_input.response_type}\n"
        f"Source document IDs: {sources}\n"
        f"Retrieved policy context: {policy_block}\n"
        f"Verified order lookup: {order_block}\n"
        f"Draft answer: {review_input.draft_answer}\n"
    )


def build_review_input_from_crew(
    user_query: str,
    structured: SupportCrewResponse,
    crew_result: dict[str, Any],
) -> AutogenReviewInput:
    policy_context: str | None = None
    source_ids = list(structured.sources)
    order_payload = None

    rag_trace = crew_result.get("rag_tool_trace") or []
    if rag_trace:
        payload = rag_trace[-1].get("payload") or {}
        policy_context = str(payload.get("supporting_context") or payload.get("answer") or "")
        if not source_ids:
            source_ids = sorted(
                {
                    chunk.get("document_id")
                    for chunk in payload.get("retrieved_chunks", [])
                    if chunk.get("document_id")
                }
            )

    order_trace = crew_result.get("order_tool_trace") or []
    if order_trace:
        order_payload = order_trace[-1].get("payload")

    return AutogenReviewInput(
        user_query=user_query,
        draft_answer=structured.answer,
        response_type=structured.response_type,
        source_document_ids=source_ids,
        policy_context=policy_context,
        order_payload=order_payload,
    )


def _review_context_blob(review_input: AutogenReviewInput) -> str:
    parts: list[str] = []
    if review_input.policy_context:
        parts.append(review_input.policy_context)
    if review_input.order_payload:
        parts.append(json.dumps(review_input.order_payload, sort_keys=True))
    return "\n".join(parts) if parts else ""


def _extract_verdict(task_result: Any) -> ReviewVerdict | None:
    for message in reversed(task_result.messages):
        if isinstance(message, StructuredMessage):
            content = message.content
            if isinstance(content, ReviewVerdict):
                return content
            if isinstance(content, dict):
                return ReviewVerdict.model_validate(content)
    return None


def _agent_turn_count(task_result: Any, agent_name: str) -> int:
    count = 0
    for message in task_result.messages:
        if isinstance(message, (TextMessage, StructuredMessage)) and message.source == agent_name:
            count += 1
    return count


def build_autogen_review_team(
    client: DeterministicMockChatCompletionClient | None = None,
) -> tuple[RoundRobinGroupChat, DeterministicMockChatCompletionClient, AssistantAgent, AssistantAgent]:
    model_client = client or DeterministicMockChatCompletionClient()

    compliance_reviewer = AssistantAgent(
        POLICY_COMPLIANCE_REVIEWER_NAME,
        description="Policy Compliance Reviewer",
        model_client=model_client,
        system_message=(
            "You are the Policy Compliance Reviewer. Inspect the CrewAI draft, compare it "
            "with retrieved policy context and verified order lookup data, and flag unsupported "
            "or incorrect claims for the Final Editor. Do not emit the final user verdict."
        ),
    )

    final_editor = AssistantAgent(
        FINAL_EDITOR_NAME,
        description="Final Editor",
        model_client=model_client,
        system_message=(
            "You are the Final Editor. Read the draft, source context, and compliance feedback. "
            "Approve unchanged when fully supported, otherwise revise. Emit a structured verdict."
        ),
        output_content_type=ReviewVerdict,
    )

    team = RoundRobinGroupChat(
        [compliance_reviewer, final_editor],
        max_turns=AUTOGEN_MAX_TURNS,
        custom_message_types=[StructuredMessage[ReviewVerdict]],
    )
    return team, model_client, compliance_reviewer, final_editor


async def run_autogen_review_async(review_input: AutogenReviewInput) -> dict[str, Any]:
    team, client, _, _ = build_autogen_review_team()
    task_text = format_review_task_package(review_input)
    task_result = await team.run(task=task_text)
    verdict = _extract_verdict(task_result)

    return {
        "stop_reason": task_result.stop_reason,
        "model_client_calls": client.create_call_count,
        "max_turns": AUTOGEN_MAX_TURNS,
        "compliance_turns": _agent_turn_count(task_result, POLICY_COMPLIANCE_REVIEWER_NAME),
        "editor_turns": _agent_turn_count(task_result, FINAL_EDITOR_NAME),
        "messages": [
            {
                "source": getattr(message, "source", None),
                "type": type(message).__name__,
                "content": getattr(message, "content", None),
            }
            for message in task_result.messages
        ],
        "review_input": asdict(review_input),
        "verdict": verdict.model_dump() if verdict else None,
        "verdict_model": verdict,
        "context_blob": _review_context_blob(review_input),
    }


def run_autogen_review(review_input: AutogenReviewInput) -> dict[str, Any]:
    return asyncio.run(run_autogen_review_async(review_input))


def apply_review_verdict_to_structured(
    structured: SupportCrewResponse,
    verdict: ReviewVerdict | None,
) -> SupportCrewResponse:
    if verdict is None:
        return structured
    return structured.model_copy(update={"answer": verdict.final_answer})

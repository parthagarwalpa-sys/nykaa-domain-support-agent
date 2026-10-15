"""Part 4 Task 15 — least autonomy, risk classification, runtime budget."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from app.crew_tools import lookup_order_status, rag_policy_lookup
from app.support_crew import (
    COMPOSER_AGENT_ROLE,
    LOOKUP_AGENT_ROLE,
    RETRIEVAL_AGENT_ROLE,
    build_support_crew,
)

RiskLevel = Literal["Low", "Medium", "High"]

# Masai risk scheme — Nykaa capstone customer-support (synthetic data, policy + order lookup).
SYSTEM_RISK_LEVEL: RiskLevel = "Medium"
SYSTEM_RISK_RATIONALE = (
    "This capstone system is classified as Medium risk because it automates customer-support "
    "interactions: grounded policy guidance from a demo knowledge base, synthetic order-status "
    "lookups, and escalation signals that could influence support handling. It does not make "
    "high-stakes medical, employment, credit, or live financial-account decisions, so it is "
    "above Low (simple summarization) but below High (sensitive regulated decision domains)."
)

BUDGET_UNIT = "estimated_tokens"
# Deterministic capstone runtime cap (not commercial API billing).
MAX_REQUEST_BUDGET_TOKENS = 1024
BUDGET_ESTIMATION_FORMULA = "estimated_tokens = ceil(len(text) / 4)"

ORDER_LOOKUP_TOOL_NAME = lookup_order_status.name
RAG_TOOL_NAME = rag_policy_lookup.name

REQUEST_BUDGET_EXCEEDED_OUTCOME = "request_budget_exceeded"
REQUEST_BUDGET_EXCEEDED_REFUSAL = (
    "Your request exceeds the configured runtime token budget and cannot be processed. "
    "Please shorten the message and try again."
)

# CrewAI agent capability boundary (Python imports of check_order_status remain for Task 6/API).
AUTHORIZED_ORDER_LOOKUP_AGENT_ROLE = LOOKUP_AGENT_ROLE


class UnauthorizedAgentCapabilityError(PermissionError):
    """Raised when a non-Lookup agent attempts to resolve the order-status tool."""

    def __init__(self, agent_role: str, capability: str) -> None:
        self.agent_role = agent_role
        self.capability = capability
        super().__init__(
            f"Agent role {agent_role!r} is not authorized for capability {capability!r}. "
            f"Only {AUTHORIZED_ORDER_LOOKUP_AGENT_ROLE!r} may use order lookup."
        )


@dataclass(frozen=True)
class BudgetAssessment:
    estimated_tokens: int
    budget_cap_tokens: int
    within_budget: bool
    sanitized_text_length: int


@dataclass(frozen=True)
class AgentCapabilityRow:
    agent_role: str
    tool_names: tuple[str, ...]


def estimate_request_tokens(text: str) -> int:
    """Deterministic token estimate for governance (MOCK_LLM capstone)."""
    if not text:
        return 1
    return max(1, math.ceil(len(text) / 4))


def assess_request_budget(sanitized_text: str) -> BudgetAssessment:
    estimated = estimate_request_tokens(sanitized_text)
    return BudgetAssessment(
        estimated_tokens=estimated,
        budget_cap_tokens=MAX_REQUEST_BUDGET_TOKENS,
        within_budget=estimated <= MAX_REQUEST_BUDGET_TOKENS,
        sanitized_text_length=len(sanitized_text),
    )


def _agent_tool_names(agent: Any) -> tuple[str, ...]:
    names: list[str] = []
    for tool in getattr(agent, "tools", None) or []:
        name = getattr(tool, "name", None)
        if name:
            names.append(str(name))
    return tuple(sorted(names))


def agent_capability_matrix() -> list[AgentCapabilityRow]:
    _, _, agents = build_support_crew()
    return [
        AgentCapabilityRow(agent_role=str(agent.role), tool_names=_agent_tool_names(agent))
        for agent in agents
    ]


def capability_matrix_as_dict() -> list[dict[str, Any]]:
    return [
        {"agent_role": row.agent_role, "tool_names": list(row.tool_names)}
        for row in agent_capability_matrix()
    ]


def resolve_order_lookup_tool_for_role(agent_role: str) -> Any:
    """
    CrewAI capability boundary: only Order Lookup Agent may resolve order-status tool.
    """
    if agent_role != AUTHORIZED_ORDER_LOOKUP_AGENT_ROLE:
        raise UnauthorizedAgentCapabilityError(agent_role, ORDER_LOOKUP_TOOL_NAME)
    return lookup_order_status


def assert_least_autonomy_enforced() -> None:
    matrix = {row.agent_role: row.tool_names for row in agent_capability_matrix()}
    retrieval_tools = matrix[RETRIEVAL_AGENT_ROLE]
    lookup_tools = matrix[LOOKUP_AGENT_ROLE]
    composer_tools = matrix[COMPOSER_AGENT_ROLE]

    if ORDER_LOOKUP_TOOL_NAME in retrieval_tools:
        raise AssertionError("Retrieval Agent must not have order lookup tool")
    if ORDER_LOOKUP_TOOL_NAME in composer_tools:
        raise AssertionError("Composer Agent must not have order lookup tool")
    if ORDER_LOOKUP_TOOL_NAME not in lookup_tools:
        raise AssertionError("Order Lookup Agent must have order lookup tool")
    if RAG_TOOL_NAME not in retrieval_tools:
        raise AssertionError("Retrieval Agent must retain RAG tool")


def governance_four_layer_framing() -> dict[str, str]:
    """Masai four-layer AI governance framing (documentation only — no extra gates)."""
    return {
        "application_layer": (
            "Least autonomy: only Order Lookup Agent is wired to lookup_order_status / Task 6."
        ),
        "runtime_layer": (
            f"Per-request budget cap ({MAX_REQUEST_BUDGET_TOKENS} {BUDGET_UNIT}) rejects oversized input before crew/tools."
        ),
        "data_layer": (
            "Task 10 PII masking before processing/logging; synthetic capstone dataset and KB only."
        ),
        "evaluation_layer": (
            "Task 13 mock-judge evaluation and Task 4 retrieval fallback for groundedness."
        ),
    }

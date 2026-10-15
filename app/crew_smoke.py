"""Single-agent CrewAI kickoff smoke harness for order lookup tool verification."""

from __future__ import annotations

import os
from typing import Any

from crewai import Agent, Crew, Process, Task

from app.mock_llm import MockCrewLLM
from app.smoke_tools import check_order_status_smoke, reset_order_lookup_trace


def _ensure_offline_crewai_env() -> None:
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")


def run_order_lookup_crew_smoke(record_id: str = "NYK-SMOKE-001") -> dict[str, Any]:
    """Run a real CrewAI kickoff that must invoke the order lookup tool."""
    _ensure_offline_crewai_env()
    reset_order_lookup_trace()

    mock_llm = MockCrewLLM(model="mock-crew-llm")
    lookup_agent = Agent(
        role="Order Lookup Agent",
        goal="Look up synthetic order status using the provided tool.",
        backstory="Offline smoke agent for Step 1B verification.",
        tools=[check_order_status_smoke],
        llm=mock_llm,
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description=(
            f"Find the current status for order {record_id}. "
            "You must use the order lookup tool before answering."
        ),
        expected_output="A concise answer grounded in the tool JSON output.",
        agent=lookup_agent,
    )

    crew = Crew(
        agents=[lookup_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    raw = str(result.raw) if hasattr(result, "raw") else str(result)

    from app.smoke_tools import ORDER_LOOKUP_CALL_COUNT, ORDER_LOOKUP_TRACE

    return {
        "kickoff_output": raw,
        "tool_call_count": ORDER_LOOKUP_CALL_COUNT,
        "tool_trace": ORDER_LOOKUP_TRACE,
        "mock_llm_calls": mock_llm.call_count,
    }

"""Part 2 Task 7 — three-agent CrewAI support crew (RAG + order lookup + composer)."""

from __future__ import annotations

import os
from typing import Any

from crewai import Agent, Crew, Process, Task

from app import crew_tools
from app.crew_tools import TASK7_RAG_COLLECTION, lookup_order_status, rag_policy_lookup, reset_crew_tool_traces
from app.crew_schemas import SupportCrewResponse, validate_support_crew_response
from app.nykaa_mock_llm import NykaaMockCrewLLM

RETRIEVAL_AGENT_ROLE = "Retrieval Agent"
LOOKUP_AGENT_ROLE = "Order Lookup Agent"
COMPOSER_AGENT_ROLE = "Response Composer Agent"

POLICY_DEMO_QUERY = "What is the return eligibility for unused sealed Beauty products?"
ORDER_DEMO_QUERY = "Check the status of order NYK-20261013-0005."
ORDER_DEMO_RECORD_ID = "NYK-20261013-0005"


def ensure_offline_crewai_env() -> None:
    os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"


def build_support_crew(mock_llm: NykaaMockCrewLLM | None = None) -> tuple[Crew, NykaaMockCrewLLM, list[Agent]]:
    ensure_offline_crewai_env()
    llm = mock_llm or NykaaMockCrewLLM(model="nykaa-mock-crew-llm")

    retrieval_agent = Agent(
        role=RETRIEVAL_AGENT_ROLE,
        goal="Retrieve grounded Nykaa demo policy context using the RAG tool when asked policy questions.",
        backstory="You only answer policy topics via rag_policy_lookup; never invent policy text.",
        tools=[rag_policy_lookup],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    lookup_agent = Agent(
        role=LOOKUP_AGENT_ROLE,
        goal="Look up real capstone orders using lookup_order_status when a record_id is provided.",
        backstory="You use Task 6 check_order_status via the lookup tool; never fabricate order data.",
        tools=[lookup_order_status],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    composer_agent = Agent(
        role=COMPOSER_AGENT_ROLE,
        goal="Combine upstream retrieval and lookup outputs into one final draft without adding unsupported facts.",
        backstory="You synthesize only what prior agents/tool JSON provided.",
        tools=[],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    agents = [retrieval_agent, lookup_agent, composer_agent]

    retrieval_task = Task(
        description=(
            "Process the customer request: {query}\n"
            "If this is a policy question, you MUST call rag_policy_lookup before answering."
        ),
        expected_output="Grounded policy retrieval JSON or explicit skip note.",
        agent=retrieval_agent,
    )

    lookup_task = Task(
        description=(
            "Process the customer request: {query}\n"
            "If a NYK-20261013 record_id is present, you MUST call lookup_order_status."
        ),
        expected_output="Order status JSON from Task 6 or explicit skip note.",
        agent=lookup_agent,
        context=[retrieval_task],
    )

    compose_task = Task(
        description=(
            "Draft the final customer-facing answer for: {query}\n"
            "Use ONLY upstream retrieval/lookup outputs. Do not invent policy or order facts."
        ),
        expected_output="Structured SupportCrewResponse grounded in tool outputs.",
        agent=composer_agent,
        context=[retrieval_task, lookup_task],
        output_pydantic=SupportCrewResponse,
    )

    crew = Crew(
        agents=agents,
        tasks=[retrieval_task, lookup_task, compose_task],
        process=Process.sequential,
        verbose=False,
    )
    return crew, llm, agents


def extract_validated_crew_response(kickoff_result: Any) -> SupportCrewResponse:
    if hasattr(kickoff_result, "pydantic") and kickoff_result.pydantic is not None:
        return validate_support_crew_response(kickoff_result.pydantic)
    if hasattr(kickoff_result, "tasks_output") and kickoff_result.tasks_output:
        for task_output in reversed(kickoff_result.tasks_output):
            if getattr(task_output, "pydantic", None) is not None:
                return validate_support_crew_response(task_output.pydantic)
    raise ValueError("Crew kickoff did not produce a validated SupportCrewResponse")


def run_support_crew_kickoff(user_query: str) -> dict[str, Any]:
    reset_crew_tool_traces()
    crew, mock_llm, agents = build_support_crew()
    result = crew.kickoff(inputs={"query": user_query})
    raw = str(result.raw) if hasattr(result, "raw") else str(result)
    structured = extract_validated_crew_response(result)

    return {
        "query": user_query,
        "kickoff_output": raw,
        "kickoff_used": True,
        "response_format_model": SupportCrewResponse.__name__,
        "structured_response": structured.model_dump(),
        "rag_collection": TASK7_RAG_COLLECTION,
        "mock_llm_calls": mock_llm.call_count,
        "rag_tool_call_count": crew_tools.RAG_POLICY_CALL_COUNT,
        "order_tool_call_count": crew_tools.ORDER_STATUS_CALL_COUNT,
        "rag_tool_trace": list(crew_tools.RAG_POLICY_TRACE),
        "order_tool_trace": list(crew_tools.ORDER_STATUS_TRACE),
        "agent_roles": [agent.role for agent in agents],
    }


def run_policy_demo() -> dict[str, Any]:
    return run_support_crew_kickoff(POLICY_DEMO_QUERY)


def run_order_demo() -> dict[str, Any]:
    return run_support_crew_kickoff(ORDER_DEMO_QUERY)


def crew_topology() -> dict[str, Any]:
    return {
        "agent_count": 3,
        "agents": [
            {
                "role": RETRIEVAL_AGENT_ROLE,
                "tools": ["rag_policy_lookup"],
            },
            {
                "role": LOOKUP_AGENT_ROLE,
                "tools": ["lookup_order_status"],
            },
            {
                "role": COMPOSER_AGENT_ROLE,
                "tools": [],
            },
        ],
        "process": "sequential",
        "rag_collection": TASK7_RAG_COLLECTION,
        "llm": "NykaaMockCrewLLM (crewai.llms.base_llm.BaseLLM)",
    }

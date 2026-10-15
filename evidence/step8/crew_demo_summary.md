# Task 7 Crew demonstrations

## Topology

```json
{
  "agent_count": 3,
  "agents": [
    {
      "role": "Retrieval Agent",
      "tools": [
        "rag_policy_lookup"
      ]
    },
    {
      "role": "Order Lookup Agent",
      "tools": [
        "lookup_order_status"
      ]
    },
    {
      "role": "Response Composer Agent",
      "tools": []
    }
  ],
  "process": "sequential",
  "rag_collection": "nykaa_fixed_chunks",
  "llm": "NykaaMockCrewLLM (crewai.llms.base_llm.BaseLLM)"
}
```

## Policy query

- Query: What is the return eligibility for unused sealed Beauty products?
- RAG tool calls: 1
- Order tool calls: 0

## Order query

- Query: Check the status of order NYK-20261013-0005.
- RAG tool calls: 0
- Order tool calls: 1

See `crew_demo_transcripts.json` for kickoff outputs and traces.

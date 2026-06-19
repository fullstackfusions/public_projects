# Agentic Chat Backend — Multi-Agent AI Orchestration

**Port:** 8010 | **Stack:** FastAPI + LangGraph + MCP + Redis

Demonstrates how to build an AI system where multiple specialized agents collaborate to answer questions. A central "orchestrator" agent routes questions to sub-agents, each with their own set of tools.

**API docs:** http://localhost:8010/docs

> **Note:** This service requires an `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` to be set in your environment.

---

## What You'll Learn

- Multi-agent architectures — how to break complex AI tasks into specialized agents
- LangGraph — a library for building stateful, multi-step AI pipelines
- MCP (Model Context Protocol) — a standard way to give AI agents access to tools
- The ReAct pattern — how agents alternate between Reasoning and Acting
- Async job queues with Redis — submit a job, poll for results

---

## The Core Idea

Instead of one AI that tries to do everything, you have specialized agents:

```
User asks: "What devices are in site A and what's their CPU usage?"

CentralAgent (orchestrator)
  → sees the question has two parts
  → calls InventoryAgent: "What devices are in site A?"
  → calls GrafanaAgent: "What's the CPU usage for those devices?"
  → combines both answers into one response
```

Each sub-agent has its own set of **tools** — things it can do, like querying a database, running a command, or calling an API.

---

## Architecture

```
User Request
    ↓
CentralAgent  (decides which sub-agents to call)
    ├── InventoryAgent  → Toolbox MCP   (asset/device queries)
    ├── NetworkAgent    → Network MCP   (network diagnostics)
    ├── GrafanaAgent    → Grafana MCP   (metrics and dashboards)
    └── FlowIqAgent     → Elasticsearch MCP (network traffic data)
```

**MCP (Model Context Protocol)** is an open standard by Anthropic. An MCP server exposes tools the AI can call. The AI decides when and how to use them based on the user's question.

---

## The ReAct Pattern

Every agent follows ReAct: **Re**ason → **Act** → Observe → Repeat

```
Thought: "The user wants CPU usage. I should query Grafana."
Action: call grafana_mcp.query_prometheus({"query": "cpu_usage{host='web-01'}"})
Observation: {"cpu": 72.4}
Thought: "I have the data. I can now answer."
Final Answer: "CPU usage for web-01 is 72.4%"
```

This loop continues until the agent has enough information to answer.

---

## Async Job Pattern

Because AI inference can take several seconds, the service uses an async job pattern:

```
POST /chat  {"message": "..."}
  ← {"job_id": "abc123", "status": "pending"}

GET /chat/status/abc123
  ← {"status": "processing", "progress": ["Calling InventoryAgent..."]}

GET /chat/status/abc123
  ← {"status": "complete", "result": "Here's what I found..."}
```

Redis stores job state so multiple workers can handle jobs concurrently.

---

## Project Structure

```
backends/agentic-chat-py/
└── app/
    ├── main.py          # FastAPI app + job submission endpoint
    ├── redis_store.py   # Job state management in Redis
    └── agents/
        ├── base.py      # BaseAgent — LangGraph builder
        ├── central.py   # Orchestrator agent
        ├── grafana.py   # Grafana/metrics agent
        ├── inventory.py # ITAM/asset agent
        ├── network.py   # Network diagnostics agent
        └── flowiq.py    # Network traffic agent
```

---

## Try It

```bash
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

# Submit a question
JOB=$(curl -s -X POST http://localhost:8010/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What can you help me with?"}' | jq -r .job_id)

# Poll for the result
curl http://localhost:8010/chat/status/$JOB \
  -H "Authorization: Bearer $TOKEN"
```

---

## Key Concepts to Explore

- **Tool calling** — how the AI decides which tool to call based on the question
- **Agent routing** — how the central agent decides which sub-agent handles a request
- **Context window management** — agents summarize intermediate results to avoid hitting token limits
- **Error recovery** — what happens when a tool call fails mid-reasoning

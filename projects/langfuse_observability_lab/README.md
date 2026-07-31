# Langfuse Observability Lab

A hands-on for exactly the pain point of "supervisor -> subagent -> MCP tool"
backends: once an LLM is deciding *who* handles a request, and that decider
hands off to another LLM deciding *what tool* to call, plain logs stop being
useful. You get a wall of text across processes and no single view of "this
one user request took 6 LLM calls, 3 tool calls, 1400 tokens, and failed on
step 4." This project builds that exact shape end-to-end and wires
[Langfuse](https://langfuse.com) into it so you can see it.

## Architecture

```
user query
    │
    ▼
 supervisor (LLM #1)  ── decides: ops_agent | support_agent | finish
    │                                   │
    ├──────────────► ops_agent (LLM #2, ReAct loop)
    │                     └── MCP tools: get_order_status, refund_order, calculate
    │
    └──────────────► support_agent (LLM #2', ReAct loop)
                          └── MCP tools: search_docs, lookup_ticket

 subagent replies ──► back to supervisor ──► finish, or hand off again
```

- `agents/supervisor.py` — a LangGraph `StateGraph` where the supervisor node
  makes a structured routing decision every hop, and each subagent node
  reports back to the supervisor (so a query can bounce supervisor -> ops ->
  supervisor -> support -> finish, the "one or two back and forth" pattern
  from real usage).
- `agents/subagents.py` — each subagent is a `create_react_agent` bound to
  tools pulled live from an MCP server via `langchain-mcp-adapters`, not
  hand-coded LangChain tools. That's deliberate: it reproduces the MCP
  client/server boundary your real system has.
- `mcp_servers/ops_server.py`, `mcp_servers/knowledge_server.py` — two
  standalone MCP servers (stdio transport) with a handful of mock tools. One
  tool (`refund_order` on order `ORD-999`) always raises, on purpose, so you
  have a real failure to look at instead of only the happy path.
- `observability/langfuse_setup.py` — the actual integration. Everything
  else in this repo is scaffolding to give it something realistic to trace.

## Setup

### 1. Get a Langfuse project

Fastest path — **Langfuse Cloud** (has a free tier, nothing to host):
1. Sign up at https://cloud.langfuse.com and create a project.
2. Settings -> API Keys -> create a keypair.

Or **self-host** (matches how you'd likely run it in production):
```bash
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up -d          # postgres + clickhouse + redis + minio + web + worker
# UI at http://localhost:3000 — create an org/project, then grab API keys
```
Either way, copy `.env.example` to `.env` and fill in
`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST`.

### 2. LLM — local by default, no API key needed

```bash
ollama pull qwen2.5:7b   # any tool-calling-capable model works
ollama serve
```
To use a hosted model instead (also gets you automatic $-cost tracking in
Langfuse, since token pricing for well-known models is built in), set in
`.env`:
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

### 3. Install

```bash
cd langfuse_observability_lab
pip install -e .
```

## Running

```bash
python run.py "What's your return policy?"

python run.py "What's the status of order ORD-100?"

# Multi-hop: supervisor routes to support_agent, then ops_agent
python run.py "Confirm the return policy covers order ORD-200, then refund the full $129.50."

# Deliberate failure — refund_order raises for this order id
python run.py "Please refund the full amount for order ORD-999."

# Or run all 4 scripted scenarios under one shared session_id:
python run.py --demo --user alice
```

Each run prints a Langfuse trace URL. Open it.

## What to actually look at in Langfuse

This is the point of the exercise — map each UI feature back to the
complaint it solves:

| Your complaint | Where it shows up |
|---|---|
| "Can't tell which sub-agent/MCP handled what" | **Trace tree**: supervisor span, nested `ops_agent`/`support_agent` spans, nested tool-call spans underneath those. Click any span to see its exact input/output. |
| "Hard to find proper errors" | Run the `ORD-999` scenario, open its trace — the failing `refund_order` span is marked red with the exception and stack trace, nested under `ops_agent`, nested under the request. No grepping logs across processes. |
| "Token usage" | Every LLM span shows prompt/completion/total tokens. The trace root rolls them up across *all* hops and subagents into one total for the request. |
| "Metrics" | Dashboards tab: latency percentiles, error rate, token throughput, cost — sliceable by the `tags` this project attaches per scenario (e.g. `deliberate-failure`, `multi-hop`). |
| "Response details" | Every span's input/output is captured verbatim, including intermediate tool-call arguments and results — the stuff you'd otherwise have to reconstruct from scattered log lines. |
| "Chaos from back-and-forth" | Run the multi-hop scenario and read the trace top to bottom: supervisor's routing *reason* is captured at each hop, so you can see exactly why it bounced between agents instead of guessing. |
| Grouping requests from the same conversation/user | **Sessions** tab, filtered by the `session_id` this project sets — the `--demo` run groups all 4 scenarios under one session on purpose. |
| Was this response actually correct? | **Scores**: `run.py` attaches a `task_success` score (1/0, rule-based here) to every trace after it finishes. Swap in an LLM-as-judge or human review queue for real evals — same API. |

## Mapping this onto your real backend

The demo is intentionally small, but the integration points are exactly what
you'd touch in your LangChain/LangGraph + MCP system:

1. **One root span per user request, not per LLM call.** Wrap your top-level
   entrypoint (wherever a request enters the supervisor) in
   `langfuse_client.start_as_current_span(...)`, then call
   `span.update_trace(session_id=..., user_id=..., tags=[...])`. Use your
   real conversation/thread id as `session_id` — that's what lets you open
   Langfuse and see "everything that happened for this conversation," not
   just one turn.
2. **Thread one `CallbackHandler` through every nested `.invoke()`/`.ainvoke()`.**
   Supervisor graph, every subagent graph, every MCP tool call — all of them
   need `config={"callbacks": [handler], ...}` passed down, same as this repo
   does from `run.py` -> `supervisor.py` -> `subagents.py`. Miss one hop and
   that branch of the trace silently detaches into its own trace instead of
   nesting — that's the #1 way people get a chaotic Langfuse view that
   mirrors the chaotic logs they started with.
3. **Tag traces by which agent/MCP handled them.** `langfuse_tags` in the
   metadata dict (see `observability/langfuse_setup.py`) is cheap and makes
   the Traces table filterable by agent, which is normally the first thing
   you want when hunting a specific failure class ("show me every trace that
   touched the pricing MCP in the last hour").
4. **Score outside the model.** Don't rely on the LLM to self-report success.
   Attach scores after the fact from whatever signal you actually trust —
   a downstream status code, a user thumbs-up/down, a nightly LLM-judge
   batch job scoring recent traces via the Langfuse API.
5. **Set `LANGFUSE_SAMPLE_RATE` (env var) once volume matters.** At demo
   scale you want 100% capture; in production you typically don't need every
   trace, only errors and a sample of the rest — the SDK supports this
   without code changes.
6. **If you self-host**, put the Langfuse `docker compose` stack behind your
   internal network, not exposed publicly — full LLM inputs/outputs land in
   ClickHouse/Postgres there, so treat it like any other system that stores
   your data.

## Extending the hands-on

- Add a third subagent + MCP server and watch the supervisor's routing
  prompt/graph grow — a good stand-in for adding a real MCP to your system.
- Change `MAX_HOPS` in `agents/supervisor.py` down to 1 and rerun the
  multi-hop scenario — see the (bad) truncated answer, and see that behavior
  captured plainly in the trace instead of being a mystery.
- Swap the rule-based `task_success` score in `run.py` for a second LLM call
  that judges the final answer against the query, and attach that score
  instead — a minimal LLM-as-judge eval wired to real traces.

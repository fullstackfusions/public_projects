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
 supervisor (LLM #1)  ── decides: ops_agent | support_agent | network_agent | finish
    │                                   │                          │
    ├──────────────► ops_agent (ReAct loop)                        │
    │                     └── MCP tools: get_order_status, refund_order, calculate
    │                                                               │
    ├──────────────► support_agent (ReAct loop)                    │
    │                     └── MCP tools: search_docs, lookup_ticket │
    │                                                               │
    └──────────────► network_agent (ReAct loop) ◄───────────────────┘
                          └── MCP tools: run_command, run_commands,
                                         dns_lookup, ping_check
                              (each call wrapped in a retry loop —
                               opaque or traced, see below)

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
- `mcp_servers/ops_server.py`, `mcp_servers/knowledge_server.py`,
  `mcp_servers/network_server.py` — three standalone MCP servers (stdio
  transport) with mock tools. Several failures are deliberate, not bugs:
  - `refund_order` on order `ORD-999` always raises.
  - `network_server.py`'s `flaky-fw-03` device drops the first 2 of every 3
    connection attempts, then succeeds on the 3rd — this is the "gateway
    silently drops, we only find out after retries fail" scenario.
  - `network_server.py`'s `dead-host-04` always times out — retries never
    help, they just delay the inevitable failure.
  - `ping_check` reports 100% packet loss for `10.0.0.99` as normal (non-error)
    output — a silently degraded result, not an exception.
  - `run_commands` (bulk, multi-device) catches per-device errors and returns
    them as data instead of raising, so a batch call can look like one clean
    green span while individual devices inside it failed.
- `agents/network_client.py` — wraps every network tool call in a 3-attempt
  retry loop, in two flavors (`traced=False`/`True`) you can compare directly.
  See "Retries: opaque vs. traced" below.
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

# Network device commands, bulk batch, DNS, ping/subnet
python run.py "Run 'show version' on core-sw-01."
python run.py "Run 'show version' on core-sw-01 and 'show interfaces' on edge-rtr-02."
python run.py "Resolve flaky-fw-03.lab.internal."
python run.py "Ping subnet 10.0.0.0/29 and tell me if anything is down."

# Flaky device — retries happen invisibly by default
python run.py "Run 'show interfaces status' on flaky-fw-03."
# Same query, but each retry attempt gets its own Langfuse span
python run.py "Run 'show interfaces status' on flaky-fw-03." --traced-retries

# Dead host — retries are exhausted, then it fails for real
python run.py "Run 'show version' on dead-host-04."

# Or run the full scripted set (all of the above, plus the opaque-vs-traced
# comparison run twice) under one shared session_id:
python run.py --demo --user alice
```

Each run prints a Langfuse trace URL. Open it.

## Retries: opaque vs. traced

This is the direct answer to "does Langfuse catch it when our gateway
silently retries 3 times before we find out": **only if the retry is visible
to something Langfuse is watching.** `agents/network_client.py` implements
the exact same retry loop two ways so you can see the difference instead of
taking that on faith:

- **Opaque** (default): a plain try/except loop around the tool call. From
  LangChain/Langfuse's point of view, one tool call happened — you'll see a
  single `run_command` span whose duration is inflated by however many
  silent attempts it took, with no breakdown of "2 dropped connections then
  a working one" vs. "just slow." This is what you get for free from most
  gateway SDKs, and it's the actual blind spot.
- **Traced** (`--traced-retries`, or the network_agent built with
  `traced_retries=True`): the identical retry loop, except each attempt
  opens its own `gateway-attempt-N` span nested under the tool call, with
  its own status and captured exception. Same retry behavior underneath —
  completely different trace.

Run the flaky-device query both ways (or just `python run.py --demo`, which
runs the comparison automatically) and compare the two traces side by side —
same session, tagged `opaque-retry` and `traced-retry`. That side-by-side is
the whole point: it's not that Langfuse can't show you retries, it's that
retries buried below your instrumentation boundary don't get seen unless you
deliberately span them.

## Live streaming server (steering + cancel, no timeout-guessing)

`run.py` runs one query start-to-finish and prints a trace URL afterwards.
`server.py` is the other mode: a WebSocket server that streams the
supervisor's progress live — routing decisions, tool calls, tokens — as they
happen, and accepts a new query or a cancel *while a run is still in
flight*. This is the direct answer to "instead of guessing a timeout, let
the user watch it happen and steer/cancel themselves."

### Run it

```bash
cd langfuse_observability_lab
uvicorn server:app --reload --port 8000
```

Open **http://localhost:8000/** in a browser. That's a plain HTML/JS test
page (`static/index.html`) served by the same app — no separate frontend
build needed.

### What to try

1. **Watch a normal run.** Send `Run 'show interfaces status' on core-sw-01.`
   and watch the live log: `network_agent started` → `tool_start` →
   `tool_end` → tokens streaming in → `FINAL`.
2. **Mid-flight steering.** Send `Ping subnet 10.0.0.0/29 and tell me if
   anything is down.`, then — while it's still running — type a second,
   different query and hit "Send query" again. It doesn't start a second
   run; it's queued and picked up at the *next* supervisor hop (you'll see
   a pink "queued steering input" line, then the supervisor's next routing
   decision reacting to it). This only ever takes effect between hops, never
   mid-tool-call, so an in-flight MCP call always finishes cleanly.
3. **Soft cancel.** Send `Run 'show version' on dead-host-04.` (a ~timeout
   scenario) and hit "Cancel (soft)". The current tool call is allowed to
   finish/fail on its own; the supervisor then force-finishes instead of
   routing further.
4. **Hard cancel.** Same query, but hit "Cancel (hard)" — the whole run is
   cancelled immediately via `asyncio.Task.cancel()`, mid-call. Fine for
   read-only tools; think twice before doing this for a tool with real
   side effects (a refund call cut off mid-flight has no record of whether
   it completed).

### How it's wired

- `graph.astream_events(..., version="v2")` emits every node/tool/token
  event as the graph runs — the same callback machinery the Langfuse
  `CallbackHandler` uses, so this run is traced in Langfuse exactly like any
  `run.py` invocation (session-tagged `live-stream`), with zero extra
  instrumentation.
- Steering: a per-connection `asyncio.Queue`, drained at the top of
  `supervisor_node` (`agents/supervisor.py`) before it makes its next
  routing decision — see the "Mid-flight steering" comment there.
- Cancel: a per-connection `asyncio.Event` checked at the same point (soft),
  or a direct `task.cancel()` on the run's `asyncio.Task` (hard).
- The steering/cancel objects travel through `config["configurable"]`,
  the same `config` dict that already carries the Langfuse callback handler
  down through every subagent call — one plumbing mechanism doing both jobs.

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
| Grouping requests from the same conversation/user | **Sessions** tab, filtered by the `session_id` this project sets — `--demo` groups every scenario under one session on purpose. |
| Was this response actually correct? | **Scores**: `run.py` attaches a `task_success` score (1/0, rule-based here) to every trace after it finishes. Swap in an LLM-as-judge or human review queue for real evals — same API. |
| "Gateway silently retries, we only find out after 3 fail" | Run the flaky-device query with and without `--traced-retries` (or `--demo`) and compare the two traces — one inflated span vs. three visible `gateway-attempt-N` spans. See "Retries: opaque vs. traced" below. |
| "MCP call times out" | The `dead-host-04` scenario — its tool span is red with a `TimeoutError` and a duration you can alert on, nested under `network_agent`, nested under the request. |
| A tool call that "succeeded" but the data underneath was bad | The subnet-ping scenario — `ping_check`'s span is green (no exception), but the JSON output for `10.0.0.99` shows 100% loss. And the bulk-command scenario — `run_commands`' span is green even though one of the three devices in it failed. Both are real gaps a red/green trace view alone won't catch; you still have to look at (or explicitly score) the payload. |

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
3. **Make retries visible or accept you won't see them.** If your enterprise
   LLM gateway or MCP client retries internally before returning, Langfuse
   sees one call with inflated latency, full stop — it cannot see inside a
   library you don't control. Either use retry mechanisms that live above
   your instrumentation boundary (e.g. LangChain's `.with_retry()`, called
   with the same `config` so each attempt gets its own callback events), or,
   when the retry genuinely has to live inside a vendored client, wrap it
   yourself and open one span per attempt like `agents/network_client.py`
   does. The same applies to your 120s-per-LLM-call timeout: a timeout that
   raises shows up as a red generation span you can alert on; a timeout that
   gets silently swallowed and retried by SDK code below LangChain does not.
4. **Tag traces by which agent/MCP handled them.** `langfuse_tags` in the
   metadata dict (see `observability/langfuse_setup.py`) is cheap and makes
   the Traces table filterable by agent, which is normally the first thing
   you want when hunting a specific failure class ("show me every trace that
   touched the pricing MCP in the last hour").
5. **Score outside the model.** Don't rely on the LLM to self-report success.
   Attach scores after the fact from whatever signal you actually trust —
   a downstream status code, a user thumbs-up/down, a nightly LLM-judge
   batch job scoring recent traces via the Langfuse API.
6. **Set `LANGFUSE_SAMPLE_RATE` (env var) once volume matters.** At demo
   scale you want 100% capture; in production you typically don't need every
   trace, only errors and a sample of the rest — the SDK supports this
   without code changes.
7. **If you self-host**, put the Langfuse `docker compose` stack behind your
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
- In `agents/network_client.py`, add a real backoff (`await asyncio.sleep(2 ** attempt)`)
  and rerun the flaky/dead-host scenarios — watch the trace durations actually
  reflect the backoff instead of the near-instant demo timing.
- Point `MAX_RETRIES` in `agents/network_client.py` at an env var and drop it
  to 1 — rerun `dead-host-04` and see how much sooner the failure surfaces
  end-to-end vs. exhausting 3 attempts first, which is the real tradeoff
  behind "how many retries should our gateway do."

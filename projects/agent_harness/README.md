# Agent Harness — Hands-On Projects

Three experiments exploring how harness infrastructure (not model capability) determines agent reliability — and what changes when you swap hand-built primitives for a harness library.

---

## Projects

```
agent_harness/
├── harness_ladder/          # Controlled benchmark: measure each infrastructure layer's impact
├── multi_agent_coding/      # Production-closer pipeline: 4 specialist agents in sequence
└── deep_research_agent/     # Library version: same harness ideas via LangChain's deepagents
```

---

## Project 1: `harness_ladder`

A controlled experiment to measure how much each infrastructure layer actually improves an LLM coding agent. The metaphor is a ladder — each *rung* adds exactly one component, and you can run a benchmark sweep to see the pass-rate delta per rung.

### The 6 Rungs

| Rung | What's added | Core lesson |
|------|-------------|-------------|
| 0 | Bare ReAct loop — model + tools only | Baseline |
| 1 | Planning tools (`create_plan`, `mark_step_done`) | Structural decomposition alone boosts even weaker models |
| 2 | Scratch memory (`scratch_write/read`) | Many failures are context failures, not capability failures |
| 3 | Auto-verify node (harness runs tests, re-injects failures) | The harness enforces the feedback loop — the model doesn't choose it |
| 4 | Sandboxed write (only `solution.py` writable) | Ashby's Law — blocking bad moves is cheaper than asking the model to avoid them |
| 5 | Sub-agent delegation (`delegate_subtask`) | Isolated context per sub-problem beats one long accumulating context |

### Graph Shape

```
Rung 0–2:   START → agent → (tool_calls?) → tools → agent → ... → END

Rung 3–5:   START → agent → (tool_calls?) → tools → agent
                                           → (done?)    → verify → (passed?) → END
                                                                  → (failed?) → agent
```

### Key Architectural Point

Rung 3 is the biggest conceptual jump. Before it, tests are a tool the model *can* call. After it, verification is a LangGraph node the harness *forces* — completely outside the model's control. The model cannot skip the feedback loop.

The eval runner (`eval/runner.py`) produces a structured `(model, rung, task, pass/fail)` table so you can plot whether adding each rung is worth the added complexity and latency cost.

### Running

```bash
cd harness_ladder
python run_experiment.py
```

---

## Project 2: `multi_agent_coding`

A production-closer multi-agent pipeline where 4 *specialist* agents work in a fixed sequence, each with a single focused role. Runs fully locally via Ollama (no cloud API needed). Generates a `proof.md` document per run as an audit trail.

### The 4 Agents

```
START → PLANNER → CODER → EVALUATOR ──── pass ──────────────→ END
                                └── fail, iter < 3 ──→ DEBUGGER → EVALUATOR
                                └── fail, iter >= 3 ──────────→ END
```

| Agent | Role | LLM? |
|-------|------|------|
| PLANNER | Decomposes task into steps + edge cases. No code produced. | Yes |
| CODER | Writes full `solution.py` from the plan. Strict output rules — one code block, all imports, no placeholders. | Yes |
| EVALUATOR | Runs pytest, returns structured pass/fail. | No — pure subprocess |
| DEBUGGER | Reads failing assertion lines, does root-cause analysis, patches `solution.py`. Max 3 attempts. | Yes |

### Key Design Decisions

- The EVALUATOR has zero LLM involvement — it is a deterministic subprocess node. Separation of reasoning vs. enforcement is intentional.
- `_parse_failures()` surgically extracts assertion lines and failed test names so the DEBUGGER receives a focused signal, not raw pytest noise.
- LangGraph streaming is used in `run.py` to show real-time per-agent progress without buffering the full run.
- Proof documents are written to `proofs/` after every run — each proof captures what each agent reasoned, timing, and the final result.

### Running

```bash
cd multi_agent_coding

# Recommended first run (email validator)
python run.py --demo 1

# Other demos
python run.py --demo 2          # URL slug generator
python run.py --demo 3          # run-length encoding

# Use a different model
python run.py --demo 1 --model qwen3:8b
python run.py --demo 1 --model claude-sonnet-4-6   # needs ANTHROPIC_API_KEY

# Your own task
python run.py --task "implement X" --tests path/to/test.py
```

---

## Project 3: `deep_research_agent`

The library counterpart to the two hand-built projects above. Instead of wiring every node, edge, and tool by hand, `create_deep_agent()` from LangChain's `deepagents` supplies the harness. We bring only two things: **one domain tool** (DuckDuckGo web search, no API key) and **a delegation plan** (two subagents). The orchestrator plans, delegates research to isolated subagents, synthesizes a sourced `report.md`, has a critic review it, and revises.

### What deepagents provides vs. what we hand-wired

| Capability | Hand-built (`multi_agent_coding` / `harness_ladder`) | `deepagents` (this project) |
|---|---|---|
| Planning / task tracking | `create_plan` / `mark_step_done` wired at rung 1 | `write_todos` middleware — free |
| Scratch + deliverable memory | `scratch_write/read`, manual JSON files | virtual filesystem (`read_file`/`write_file`/`edit_file`/`ls`/`glob`/`grep`) — free |
| Subagent delegation | `delegate_subtask` hand-built at rung 5 | `task` tool + `subagents=[...]` — free |
| Isolated context per sub-problem | manual sub-graph invocation | automatic — each `task` call runs in its own window |
| **The deterministic gate** | **`EVALUATOR` = pure pytest subprocess, no LLM** | **NOT provided — the `critic-subagent` advises; it does not enforce** |

The last row is the lesson. `deepagents` collapses planning + memory + delegation into a few lines, but will not give you the no-LLM enforcement node that `multi_agent_coding`'s EVALUATOR represents. A library hands you the harness *structure*; the *enforcement boundary* is still a design decision you own.

### Architecture

```
deep researcher (orchestrator)
    │  1. plan sub-questions      →  write_todos
    │  2. delegate each           →  task("research-subagent", …)   ← isolated context
    │  3. orchestrator saves text →  write_file("findings/<slug>.md")
    │  4. synthesize report.md    →  read_file + write_file
    │  5. have it reviewed        →  task("critic-subagent", …)
    └─ 6. revise & finalize       →  edit_file
```

**Key VFS lesson discovered during this hands-on:** subagents run in isolated context windows — files written *inside* a subagent do not propagate back to the orchestrator's virtual filesystem. The fix: subagents return findings as text (the natural `task` tool return value), and the orchestrator is the only one that calls `write_file`. All VFS writes must happen in the context that persists.

### Local inference on Apple M3 — what we learned

The initial run used 5 sub-questions (the orchestrator's "3–6" default). On an M3 MacBook with `qwen3:8b` this produced:

- **~619 seconds** of total run time
- **llama-server peaked at 7.77 GB** RAM (vs. a typical ~5 GB for a single call)
- Sustained fan noise + heat throughout

The spike to 7.77 GB was not expected from an "8B" model. The cause: **`qwen3:8b` is a reasoning model with a built-in chain-of-thought mode.** When the orchestrator faces a complex delegation task it activates extended internal reasoning, which expands the KV cache significantly — well beyond what a plain 8B model would use. This is the same phenomenon you see with DeepSeek-R1 or o1-style models: more inference passes × reasoning overhead = non-linear memory growth.

Reducing to **3 sub-questions** brought the run down to **223 seconds** and kept RAM more stable, while still producing a complete sourced report with critique. The tradeoff is report depth vs. local resource cost. For production-quality output, cloud models (`--model claude-opus-4-8`) are the right call — zero local compute, 3–5× faster.

### Running

```bash
cd deep_research_agent
pip install -e .
ollama pull qwen3:8b    # must support tool calling — gemma3 does NOT

python run.py --brief 1  # deepagents vs Agents SDK vs CrewAI
python run.py --brief 2  # EU AI Act obligations for agents
python run.py --brief 3  # Kafka vs Redpanda vs Kinesis

# Lighter local run (no reasoning overhead):
python run.py --brief 1 --model qwen2.5:7b

# Cloud (offloads compute entirely; needs ANTHROPIC_API_KEY in .env):
python run.py --brief 1 --model claude-opus-4-8
```

---

## Harness Engineering Landscape

These projects sit inside a broader ecosystem of agent harness frameworks. Understanding where they fit is part of the exercise.

### The Two Categories (don't conflate them)

| | **goose** (AAIF / Block) | **deepagents** (LangChain) | **This repo** (hand-built) |
|---|---|---|---|
| **What it is** | A finished agent product — desktop app + CLI + API | A harness library — you build agents with it | A harness you construct from primitives |
| **You interact via** | Config: tool permissions, MCP extensions, YAML Recipes, model routing | Code: `create_deep_agent()`, custom tools, filesystem backends, middleware | Code: LangGraph nodes, edges, tool factories |
| **Harness internals** | Mostly baked in; you tune from the outside | Exposed; you compose, override, replace any piece | Fully exposed — you write every node |
| **Runtime** | Its own | LangGraph — checkpointing, HITL, streaming, durable execution | LangGraph — same runtime as deepagents |
| **Best for** | Feeling a mature harness work; off-the-shelf baseline | Building the harness with library support | Understanding what the harness actually does at each layer |

### Why we built from primitives instead of using deepagents

`deepagents` is the natural production choice — it's MIT-licensed, built on LangGraph, and its security model matches the harness philosophy exactly: *"trust the LLM, enforce boundaries at the tool/sandbox level."*

We deliberately built below that abstraction level for one reason: **the experiment required each rung to be a single, isolated variable.** Using a library that bundles planning + memory + sandboxing together would make it impossible to measure the contribution of each component independently. Writing each rung from scratch is what produces the data.

### goose as a control group

goose (now under the Agentic AI Foundation at the Linux Foundation — the Kubernetes/CNCF move of the agent runtime layer) is best used as a **baseline**: run the same task through goose with default config to answer *"what does a mature, off-the-shelf harness score?"* If your hand-built harness matches or beats it, you've learned what their defaults are doing. If it doesn't, you've found out why — which is its own lesson.

### What we did not test (yet)

- `goose` CLI — running the same demo tasks through a production harness as a control group; useful as a baseline score to compare against both the hand-built and deepagents versions
- Instrumentation via LangSmith / Langfuse — OTel trace spans per run, capturing `model`, `rung`, `tokens`, `cost_usd`, `latency_ms`, `passed`

The research notes are in `research-agent-harness-handson.md`.

---

## Tech Stack

### Orchestration & Agent Framework

| Library | Version | Role |
|---------|---------|------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | `>=0.2` / `>=1.2` | Core graph runtime — nodes, edges, conditional routing, state management, streaming |
| [LangChain](https://github.com/langchain-ai/langchain) | `>=0.3` / `>=1.3` | Tool abstractions (`@tool` decorator), message types (`SystemMessage`, `HumanMessage`) |
| `langchain-core` | `>=0.3` / `>=1.4` | `BaseChatModel`, `BaseTool`, `bind_tools` — model-agnostic interfaces |
| [deepagents](https://docs.langchain.com/oss/python/deepagents/overview) | `>=0.6.11` | LangChain's harness library — `create_deep_agent()` bundles planning (`write_todos`), virtual filesystem, and subagent delegation (`task` tool) on top of LangGraph |
| [ddgs](https://github.com/deedy5/ddgs) | `>=9.14.4` | DuckDuckGo search — no API key required; used as the web search tool in `deep_research_agent` |

### LLM Backends

| Library | Role |
|---------|------|
| [langchain-anthropic](https://github.com/langchain-ai/langchain/tree/main/libs/partners/anthropic) | Claude models via Anthropic API (`claude-sonnet-4-6`, etc.) |
| [langchain-ollama](https://github.com/langchain-ai/langchain/tree/main/libs/partners/ollama) | Local inference via Ollama — `gemma3:12b`, `qwen3:8b`, `llama`, `mistral`, `deepseek`, `phi`, `codellama` |

### Testing & Evaluation

| Library | Role |
|---------|------|
| [pytest](https://pytest.org) | Test runner — used both as the agent's evaluation target and as the harness verification mechanism |
| `subprocess` (stdlib) | EVALUATOR node runs pytest as an isolated process; test output is parsed and fed back as structured agent input |

### Observability & Output

| Library | Role |
|---------|------|
| [rich](https://github.com/Textualize/rich) | Real-time terminal output — per-agent panels, colored status, duration display |
| Proof documents (`proof.py`) | Markdown audit trail generated after each run — captures agent reasoning, timing, pass/fail per step |

### Dev & Config

| Library | Role |
|---------|------|
| `python-dotenv` | Loads `ANTHROPIC_API_KEY` and other env vars from `.env` |
| `tiktoken` | Token counting (multi_agent_coding) |
| `pandas` + `matplotlib` | Optional (`harness_ladder[plot]`) — for plotting rung vs. pass-rate sweep results |
| `hatchling` / `setuptools` | Build backends |

### Python

Both projects require **Python >= 3.11** (uses `TypedDict`, `X | Y` union syntax, and `match` patterns).

---

## Shared Design Principle

**The harness enforces correctness. The LLM provides reasoning.**

You never trust the model to self-correct — you use LangGraph nodes and sandboxing to enforce the feedback loop structurally. This distinction is the core lesson across both projects.

---

## Enterprise Applications

### `harness_ladder` as a Capability Benchmarking Framework

Enterprises face a concrete question: "does adding memory / sandboxing / sub-agents to our internal agent actually improve outcomes, and by how much?" The ladder gives a rigorous way to run that A/B comparison before committing to infrastructure investment. The eval sweep output is the evidence.

### `multi_agent_coding` as an Automated Code Generation Service

The Planner/Coder/Evaluator/Debugger pattern applies directly to:
- Generating boilerplate from internal specifications
- Auto-migrating deprecated API calls across a codebase
- Writing test coverage for legacy code
- Provisioning IaC scripts from natural language descriptions

The deterministic EVALUATOR node (no LLM in the test gate) is a hard requirement in any compliance-sensitive environment. You can swap in domain-specific validators — SQL schema checkers, API contract validators, type-checkers — using the same pattern.

### `deep_research_agent` as an Internal Intelligence Service

The plan → delegate → synthesize → critique loop maps directly to enterprise knowledge work:

- **Competitive intelligence**: hand it a brief ("compare vendor X vs Y for use case Z"); it searches, synthesizes, and produces a sourced report in minutes instead of hours
- **Regulatory scanning**: brief it on a new compliance requirement; research-subagents retrieve the relevant rules, the orchestrator drafts a gap analysis, the critic flags unsupported claims
- **Technical due diligence**: feed it a technology evaluation brief; subagents research each axis (cost, maturity, ecosystem, security posture) in parallel, the orchestrator writes the recommendation doc
- **Internal knowledge synthesis**: replace DuckDuckGo with a RAG tool over internal documents and the same architecture becomes a structured document synthesis pipeline

**Why the isolation pattern matters at enterprise scale:** each subagent runs in its own context window and returns only a distilled result. This is not just a memory optimization — it's a trust boundary. The orchestrator never sees raw search noise; it sees curated findings. The same principle applies when you replace web search with internal data sources: each specialist agent accesses only what it needs, and the orchestrator assembles the view.

**The critic pattern in production:** the `critic-subagent` is an LLM reviewer, not a deterministic gate — it advises rather than enforces. For compliance-sensitive output, replace or augment it with a rule-based checker (e.g., "every claim must contain a citation URL" enforced in Python, not by asking the model). This is the EVALUATOR lesson from `multi_agent_coding` applied to research pipelines.

---

## Next Steps: Integrating into a Real Multi-Agent Architecture

**1. Replace the EVALUATOR with domain-specific validators.**
The evaluator pattern (deterministic subprocess, not an LLM) generalizes beyond pytest. The pattern is identical — a non-LLM node that runs, returns structured pass/fail, and either exits or routes to a fixer agent. For the research pipeline, the analog is a citation checker: a Python function that verifies every claim in `report.md` contains a URL, routes back to the orchestrator on failure.

**2. Promote the scratchpad to a shared state store.**
Right now scratch is a flat JSON file per task and the deepagents VFS is in-memory per run. In a real multi-agent system this becomes a shared memory layer (Redis, a vector store, or LangGraph's built-in `MemorySaver` checkpointer) that multiple agents can read from — the PLANNER writes requirements, the CODER reads them, the DEBUGGER reads both. For the research agent, this means findings from one run are available to the next without re-searching.

**3. Add a REVIEWER agent between CODER and EVALUATOR.**
Insert a static analysis agent (or an LLM reviewer prompted to check security, style, and compliance) before tests run. This catches a whole class of failures that pytest won't catch. The `critic-subagent` in `deep_research_agent` is this pattern applied to research output — the next step is making it a hard gate rather than advisory.

**4. Wire the harness rung concept to model routing.**
In production you don't run all tasks at rung 5, and you don't run all research briefs through a reasoning model. Run a fast/cheap model first; if it fails or the output is below a quality threshold, escalate to a higher rung or a stronger model. The eval sweep data from `harness_ladder` is the evidence needed to calibrate those thresholds. For the research agent, the routing question is: does this brief need a reasoning model (qwen3, o1-style) or will a plain instruct model suffice? Local reasoning models are expensive on-device — the M3 hands-on showed a 7.77 GB peak for what nominally looks like an "8B" task.

**5. Replace web search with internal retrieval.**
Swap `internet_search` in `deep_research_agent/tools.py` with a RAG tool over internal documents — Confluence pages, Notion, Slack exports, internal wikis. The orchestrator/subagent structure stays identical; only the data source changes. This is the shortest path from the hands-on to a production internal intelligence service.

**6. Expose the pipeline as an async service.**
`run_task()` in `multi_agent_coding/system.py` and `build_research_agent()` in `deep_research_agent/research_agent.py` are already clean functions. Wrap either in a FastAPI endpoint, put a task queue (Celery/ARQ/Kafka) in front, and the agent system becomes an internal service other teams can POST jobs to and poll for results. The `proof.md` / `report.md` output becomes the response payload. LangGraph's built-in checkpointing means long-running jobs survive process restarts.

**7. Add observability from day one.**
None of these projects wire tracing — that's the next layer. LangSmith (LangChain's native OTel integration) or Langfuse add per-run spans capturing `model`, `tokens`, `cost_usd`, `latency_ms`, `tool_calls`, and `pass/fail` without changing agent logic. In production this is not optional: without per-run traces you cannot diagnose why an agent failed, which subagent produced a weak finding, or what a run cost.

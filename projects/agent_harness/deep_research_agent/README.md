# Deep Research Agent — a `deepagents` hands-on

A real-world multi-agent research system built on [LangChain's **deepagents**](https://docs.langchain.com/oss/python/deepagents/overview). Hand it a research brief; it plans the work, delegates web research to isolated subagents, drafts a sourced report on a virtual filesystem, has a critic review it, revises, and hands back `report.md`.

This is the **library-version counterpart** to the hand-built harnesses elsewhere in `agent_harness/`. In `harness_ladder` and `multi_agent_coding` we wired every node, edge, tool, and piece of state by hand. Here `create_deep_agent()` supplies the harness and we bring only two things of our own: **one domain tool** (web search) and **a delegation plan** (two subagents).

---

## The point: what you hand-wired vs. what the library gives you

| Capability | Hand-built (`multi_agent_coding` / `harness_ladder`) | `deepagents` (this project) |
|---|---|---|
| Planning / task tracking | `create_plan` / `mark_step_done` tools wired at rung 1 | `write_todos` middleware — free |
| Scratch + deliverable memory | `scratch_write/read`, manual JSON files (rung 2) | virtual filesystem (`read_file`/`write_file`/`edit_file`/`ls`/`glob`/`grep`) — free |
| Subagent delegation | `delegate_subtask` hand-built at rung 5 | `task` tool + `subagents=[...]` — free |
| Isolated context per sub-problem | manual sub-graph invocation | automatic — each `task` call runs in its own window |
| Prompt caching | not implemented | automatic on Anthropic models (n/a for local gemma) |
| **The deterministic gate** | **`EVALUATOR` = pure pytest subprocess, no LLM** | **NOT provided — you'd add it yourself** |

The last row is the lesson. `deepagents` collapses planning + memory + delegation into a few lines, but it will **not** give you the no-LLM enforcement node that `multi_agent_coding`'s EVALUATOR represents. A library can hand you the harness *structure*; the *enforcement boundary* is still a design decision you own. Here the analog is the `critic-subagent` — but note it's an LLM reviewer, not a deterministic gate, so it advises rather than enforces.

---

## Architecture

```
deep researcher (orchestrator)
    │  1. plan sub-questions      →  write_todos
    │  2. delegate each           →  task("research-subagent", …)   ← isolated context
    │  3. synthesize report.md    →  read_file + write_file
    │  4. have it reviewed        →  task("critic-subagent", …)
    └─ 5. revise & finalize       →  edit_file
```

- **`research-subagent`** — given ONE sub-question, runs several web searches in its **own** context window and writes a sourced findings file. Delegating keeps each search trace out of the orchestrator's context (the same win as ladder rung 5).
- **`critic-subagent`** — reviews the draft against the brief and returns a blunt list of gaps / unsupported claims; the orchestrator does the actual revision.

Files live in [research_agent.py](research_agent.py) (agent + subagents), [tools.py](tools.py) (web search), and [run.py](run.py) (CLI + streaming + saving the virtual FS to disk).

---

## Setup

Runs fully local by default — **no API keys**. Model is `qwen3:8b` via Ollama; web search is DuckDuckGo.

> ⚠️ **The model must support tool calling.** deepagents is built entirely on tools (planning, filesystem, delegation), so a model without tool support 400s on the first call. **`gemma3` does not support tools in Ollama** — use `qwen3`, `llama3.1`, `mistral`, or a Claude model.

```bash
# 1. Have Ollama running with a tool-capable model pulled
ollama pull qwen3:8b
ollama serve                # if it isn't already running

# 2. Install the project
cd deep_research_agent
pip install -e .
```

(`cp .env.example .env` is only needed if you later switch to a cloud model like Claude.)

## Running

```bash
python run.py --list-briefs                  # show the 3 presets

python run.py --brief 1                       # deepagents vs Agents SDK vs CrewAI
python run.py --brief 2                       # EU AI Act obligations for agents
python run.py --brief 3                       # Kafka vs Redpanda vs Kinesis

# Your own question:
python run.py --brief "Should we adopt X over Y for Z in 2026? Cover cost and ops."

# Different model (orchestrator + subagents):
python run.py --brief 1 --model llama3.1              # another tool-capable local model
python run.py --brief 1 --model claude-opus-4-8       # cloud; needs ANTHROPIC_API_KEY in .env
```

> **Local-model note:** the full plan → delegate → synthesize → critique loop leans hard on tool calling. A tool-capable 8B local model like `qwen3:8b` can drive it, but is slower and less reliable at deep subagent nesting than a frontier model — expect the occasional skipped step. It's perfect for *seeing the harness work*; switch to `--model claude-opus-4-8` when you want report quality.

The run streams live progress (planning → delegating → searching → writing → reviewing), then writes the virtual filesystem to `reports/run_<ts>/` — the deliverable is `report.md`.

---

## deepagents levers worth trying next

- **Per-subagent model override.** Add `"model": "ollama:qwen3:8b"` (or `"anthropic:claude-haiku-4-5"`) to a subagent dict in [research_agent.py](research_agent.py) to run the searcher on a smaller/faster model while the orchestrator stays on the default.
- **A deterministic gate.** To close the gap with `multi_agent_coding`, add a non-LLM step that checks `report.md` for, e.g., "every Findings bullet contains a URL" and routes back on failure — that's the EVALUATOR pattern applied here.
- **Human-in-the-loop.** `create_deep_agent(interrupt_on=...)` pauses on a named tool for approval — the production version of a sandbox boundary.
- **Persistent memory.** The `memory` parameter (AGENTS.md files) carries context across runs.

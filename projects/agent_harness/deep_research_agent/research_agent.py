"""
Deep Research Agent — built on LangChain's `deepagents`.

This is the "library version" counterpart to the hand-built harnesses in
agent_harness/. In `harness_ladder` and `multi_agent_coding` we wired every
node, edge, and tool by hand. Here we let `create_deep_agent()` supply the
harness and only bring two things of our own:

  1. a domain tool      → web search (tools.py)
  2. a delegation plan  → subagents (below)

What deepagents provides automatically (the middleware stack):

  • write_todos  — a planning loop the orchestrator uses to break a brief
                   into sub-questions and track them. (≈ rung 1 in the ladder)
  • virtual FS   — read_file / write_file / edit_file / ls / glob / grep,
                   an in-state scratch + deliverable surface. (≈ rung 2)
  • task         — spawns a subagent with an ISOLATED context window and
                   returns one consolidated report. (≈ rung 5)
  • prompt cache — automatic for Anthropic models.

Architecture (orchestrator + two specialists):

    deep researcher (orchestrator)
        │  plans sub-questions  →  write_todos
        │  delegates each       →  task("research-subagent", ...)
        │  drafts report.md     →  write_file
        │  has it reviewed      →  task("critic-subagent", ...)
        └─ revises & finalizes  →  edit_file / write_file

The two subagents exist for the same reason the ladder's rung 5 does:
isolated context per sub-problem beats one long accumulating context. Each
`research-subagent` call burns through searches in its own window and hands
back only the distilled finding — the orchestrator's context stays clean.
"""
from deepagents import create_deep_agent

from tools import internet_search

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

ORCHESTRATOR_PROMPT = """You are a principal research analyst. You produce \
rigorous, well-sourced research reports from a single brief.

Work in this order — do not skip steps:

1. PLAN. Use `write_todos` to decompose the brief into 3-4 concrete \
sub-questions (prefer 3 for local models). Each todo is one sub-question a \
specialist can answer alone.

2. DELEGATE. For each sub-question, call the `task` tool to spin up a \
`research-subagent`. Give it ONE sub-question. The subagent will return its \
findings as text — do NOT ask it to write files (it runs in an isolated context \
and those files won't reach you). After each subagent returns, YOU save its \
response with `write_file` to `findings/<short-slug>.md`. Delegate rather than \
searching yourself — this keeps each search context isolated and your own \
context clean.

3. SYNTHESIZE. Read the findings files (`ls` then `read_file`). Write a \
polished report to `report.md` with these sections:
   - Executive summary (3-5 bullets)
   - Findings (one subsection per sub-question, with inline source URLs)
   - Open questions / caveats
Every non-obvious claim must cite a source URL from the findings.

4. REVIEW. Call the `task` tool with `critic-subagent` and ask it to review \
`report.md` against the original brief. Then read its critique and revise \
`report.md` with `edit_file` / `write_file` to address every gap it raises.

5. FINISH. Your final message is a short cover note: what you concluded and \
where the full report lives (`report.md`). Do not paste the whole report into \
the message — it is already on the filesystem.

Rules: never fabricate a source. If search is unavailable or a fact cannot be \
verified, say so explicitly in the report rather than guessing."""


RESEARCH_SUBAGENT_PROMPT = """You are a focused research specialist. You are \
given exactly ONE sub-question.

Run several narrow `internet_search` queries (vary the wording; use \
topic="news"/"finance" when relevant). Read enough results to answer \
confidently. Then return your findings as structured text — the orchestrator \
will save them to a file. Do NOT use write_file; you are in an isolated context \
and your filesystem changes won't reach the orchestrator.

Your response must contain:
  - A 2-4 sentence answer to the sub-question.
  - 3-6 bullet points of key evidence, each with its source URL.
  - Any contradictions or uncertainty you noticed.

Keep it dense and sourced. Do not pad your reply — the text you return IS the \
deliverable."""


CRITIC_SUBAGENT_PROMPT = """You are a skeptical research editor. Read the \
original brief (in the task instructions) and `report.md`.

Check for: unsupported claims (assertions with no source URL), sub-questions \
from the brief that went unanswered, stale or weak sources, and internal \
contradictions. If a key claim looks shaky, you may run one or two \
`internet_search` queries to spot-check it.

Return a short, blunt list of concrete issues, most important first. If the \
report is genuinely solid, say so and stop — do not invent problems. You do \
not edit the report; the orchestrator does that."""


# ---------------------------------------------------------------------------
# Subagent definitions
# ---------------------------------------------------------------------------
# Each dict is a deepagents subagent. `tools` overrides the inherited set.
#
# Demonstrating a real deepagents lever (commented, off by default): give a
# subagent its own model — e.g. a small fast local model for searching while a
# larger one orchestrates.
#   "model": "ollama:qwen3:8b",   # or "anthropic:claude-haiku-4-5"
# Omitting "model" makes the subagent inherit the orchestrator's model.

RESEARCH_SUBAGENT = {
    "name": "research-subagent",
    "description": (
        "Answers ONE narrow research sub-question by searching the web and "
        "returning sourced findings as text. The orchestrator saves the text "
        "to a findings file. Delegate each sub-question to a separate instance "
        "so contexts stay isolated."
    ),
    "system_prompt": RESEARCH_SUBAGENT_PROMPT,
    "tools": [internet_search],
}

CRITIC_SUBAGENT = {
    "name": "critic-subagent",
    "description": (
        "Reviews a drafted report.md against the brief and returns a blunt "
        "list of gaps and unsupported claims. Use before finalizing."
    ),
    "system_prompt": CRITIC_SUBAGENT_PROMPT,
    "tools": [internet_search],
}


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_research_agent(model: str = "ollama:qwen3:8b"):
    """Construct the deep research agent.

    Args:
        model: A deepagents/`init_chat_model` provider string. The model MUST
            support tool calling (deepagents is tool-based). E.g.
            "ollama:qwen3:8b" (default, local — no API key) or
            "anthropic:claude-opus-4-8" (needs ANTHROPIC_API_KEY). Note:
            gemma3 does NOT support tools in Ollama and will fail. The
            orchestrator and (by default) both subagents run on this model.

    Returns:
        A compiled LangGraph agent. Invoke with
        `{"messages": [{"role": "user", "content": <brief>}]}`.
    """
    return create_deep_agent(
        model=model,
        tools=[internet_search],
        system_prompt=ORCHESTRATOR_PROMPT,
        subagents=[RESEARCH_SUBAGENT, CRITIC_SUBAGENT],
    )

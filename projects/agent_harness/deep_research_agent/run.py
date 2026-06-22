#!/usr/bin/env python3
"""
Deep Research Agent — entry point.

A real-world deepagents hands-on: hand it a research brief and it plans,
delegates web research to isolated subagents, drafts a sourced report on its
virtual filesystem, has a critic review it, revises, and hands back the report.

Usage:
  python run.py --brief 1                      # deepagents vs other agent frameworks
  python run.py --brief 2                      # EU AI Act obligations for agents
  python run.py --brief 3                      # event-streaming platform eval
  python run.py --list-briefs

  # Your own research question:
  python run.py --brief "Should we adopt X over Y for Z in 2026? Cover cost and ops."

  # Use a different model (orchestrator + subagents):
  python run.py --brief 1 --model llama3.1            # another tool-capable local model
  python run.py --brief 1 --model claude-opus-4-8     # needs ANTHROPIC_API_KEY

Default model is qwen3:8b via Ollama — local, no API key. Web search uses
DuckDuckGo (no key either). Just `ollama pull qwen3:8b` and go.

IMPORTANT: deepagents is built on tool calling, so the model MUST support tools.
gemma3 does NOT (Ollama returns "does not support tools"). Use qwen3, llama3.1,
mistral, or a Claude model.
"""
import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

load_dotenv()

ROOT = Path(__file__).parent
REPORTS_DIR = ROOT / "reports"
CONSOLE = Console()

PRESET_BRIEFS = {
    "1": (
        "Compare LangChain's deepagents, OpenAI's Agents SDK, and CrewAI for "
        "building production multi-agent systems as of 2026. Focus on built-in "
        "harness features (planning, memory, sandboxing), subagent support, and "
        "observability. Give a recommendation for a small engineering team."
    ),
    "2": (
        "Research the 2026 regulatory landscape for autonomous AI agents in the "
        "EU under the AI Act. Summarize the concrete compliance obligations a "
        "startup deploying customer-facing agents would have, and the timeline."
    ),
    "3": (
        "Evaluate Apache Kafka vs Redpanda vs AWS Kinesis for event streaming at "
        "a Series-A fintech in 2026. Compare cost, operational burden, ecosystem "
        "maturity, and compliance posture. Recommend one."
    ),
}

# Known langchain init_chat_model provider prefixes.
_PROVIDERS = ("anthropic", "openai", "ollama", "google_genai", "groq", "bedrock")
_OLLAMA_HINTS = ("gemma", "llama", "qwen", "mistral", "deepseek", "phi", "codellama")


def resolve_model(name: str) -> str:
    """Map a friendly model name to a deepagents `provider:model` string."""
    if name.split(":", 1)[0] in _PROVIDERS:
        return name  # already provider-prefixed (e.g. "anthropic:claude-opus-4-8")
    if "claude" in name.lower():
        return f"anthropic:{name}"
    if any(name.lower().startswith(p) for p in _OLLAMA_HINTS):
        return f"ollama:{name}"
    return f"ollama:{name}"  # default unknown names to local Ollama


# ---------------------------------------------------------------------------
# Progress display
# ---------------------------------------------------------------------------

_TOOL_DISPLAY = {
    "write_todos": ("🗺️ ", "cyan", "planning"),
    "task": ("🤝", "magenta", "delegating"),
    "internet_search": ("🔎", "blue", "searching"),
    "write_file": ("✍️ ", "green", "writing"),
    "edit_file": ("✍️ ", "green", "editing"),
    "read_file": ("📖", "yellow", "reading"),
    "ls": ("📂", "yellow", "listing"),
    "glob": ("📂", "yellow", "globbing"),
    "grep": ("🔍", "yellow", "grepping"),
}


def _short(text: str, n: int = 70) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _render_tool_call(name: str, args: dict) -> None:
    emoji, color, verb = _TOOL_DISPLAY.get(name, ("🔧", "white", name))

    if name == "task":
        sub = args.get("subagent_type") or args.get("subagent") or "subagent"
        desc = args.get("description") or args.get("task") or ""
        detail = f"[bold]{sub}[/bold] — {_short(desc)}"
    elif name == "internet_search":
        detail = f'"{_short(args.get("query", ""), 60)}"'
    elif name in ("write_file", "edit_file", "read_file"):
        detail = str(args.get("file_path") or args.get("path") or "")
    elif name == "write_todos":
        todos = args.get("todos", [])
        detail = f"{len(todos)} step(s)" if isinstance(todos, list) else ""
    else:
        detail = _short(next(iter(args.values()), "")) if args else ""

    CONSOLE.print(f"  {emoji} [{color}]{verb:<11}[/{color}] {detail}")


def _surface_messages(delta: dict) -> None:
    """Print any tool calls found in a streamed state delta."""
    for msg in delta.get("messages", []) or []:
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            continue
        for tc in tool_calls:
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
            _render_tool_call(name, args or {})


def _coerce_content(value) -> str:
    """Extract a string from a VFS entry — deepagents stores entries as dicts."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # deepagents wraps file content: {"content": "...", ...}
        for key in ("content", "text", "body", "data"):
            if isinstance(value.get(key), str):
                return value[key]
        # Last resort: dump as JSON so we don't lose data
        import json
        return json.dumps(value, indent=2)
    return str(value)


def _extract_files(state: dict) -> dict[str, str]:
    """Pull the virtual filesystem out of the final state, defensively."""
    files = state.get("files")
    if isinstance(files, dict):
        return {k: _coerce_content(v) for k, v in files.items()}
    # Fallback: find the first dict value that looks like a file map.
    for value in state.values():
        if isinstance(value, dict) and value and all(isinstance(k, str) for k in value):
            return {k: _coerce_content(v) for k, v in value.items()}
    return {}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deep Research Agent (deepagents)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--brief", help="Preset number (1-3) or a research question")
    parser.add_argument("--model", default="qwen3:8b", help="Model (default: qwen3:8b via Ollama — must support tools)")
    parser.add_argument("--list-briefs", action="store_true", help="Show preset briefs")
    args = parser.parse_args()

    if args.list_briefs:
        CONSOLE.print("\n[bold]Preset briefs:[/bold]")
        for k, v in PRESET_BRIEFS.items():
            CONSOLE.print(f"  [cyan]{k}[/cyan]  {_short(v, 90)}")
        return

    if not args.brief:
        parser.print_help()
        return

    brief = PRESET_BRIEFS.get(args.brief, args.brief)
    model = resolve_model(args.model)

    # -- Preflight ---------------------------------------------------------
    if model.startswith("anthropic:") and not os.environ.get("ANTHROPIC_API_KEY"):
        CONSOLE.print("[red]ANTHROPIC_API_KEY is not set.[/red] Add it to .env or use the default local model.")
        sys.exit(1)
    if model.startswith("ollama:"):
        CONSOLE.print(
            f"[dim]Using local Ollama model '{model.split(':', 1)[1]}'. "
            "Make sure `ollama serve` is running and the model is pulled.[/dim]\n"
        )

    CONSOLE.print()
    CONSOLE.print(Panel.fit(
        f"[bold]Deep Research Agent[/bold]  ·  built on deepagents\n"
        f"Model: [cyan]{model}[/cyan]\n"
        f"Brief: {_short(brief, 88)}",
        border_style="blue",
    ))
    CONSOLE.print()

    # -- Build & run -------------------------------------------------------
    from research_agent import build_research_agent

    agent = build_research_agent(model)
    payload = {"messages": [{"role": "user", "content": brief}]}

    t0 = time.time()
    final_state: dict = {}
    try:
        # Two stream modes at once: "updates" drives the live progress log,
        # "values" gives us the full accumulated state (incl. the virtual FS)
        # whose last emission is the final state.
        for mode, chunk in agent.stream(payload, stream_mode=["updates", "values"]):
            if mode == "updates":
                for node_name, delta in chunk.items():
                    if isinstance(delta, dict):
                        _surface_messages(delta)
            elif mode == "values":
                final_state = chunk
    except KeyboardInterrupt:
        CONSOLE.print("\n[red]Interrupted.[/red]")
        sys.exit(130)
    except Exception as exc:
        if "does not support tools" in str(exc):
            CONSOLE.print(
                "\n[red]This model can't run the agent — it has no tool-calling support.[/red]\n"
                "deepagents is built entirely on tools (planning, filesystem, delegation),\n"
                "so the model must support tool calling. [bold]gemma3 does not.[/bold]\n\n"
                "Use a tool-capable Ollama model:\n"
                "  [cyan]ollama pull qwen3:8b[/cyan]    && python run.py --brief 1 --model qwen3:8b\n"
                "  [cyan]ollama pull llama3.1:8b[/cyan] && python run.py --brief 1 --model llama3.1\n"
                "...or a Claude model with --model claude-opus-4-8.\n"
            )
            sys.exit(1)
        raise
    elapsed = time.time() - t0

    # -- Persist the virtual filesystem to disk ----------------------------
    files = _extract_files(final_state)
    out_dir = REPORTS_DIR / f"run_{int(t0)}"
    report_path = None
    for vpath, content in files.items():
        dest = out_dir / vpath.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        if Path(vpath).name == "report.md":
            report_path = dest

    # -- Summary -----------------------------------------------------------
    cover_note = ""
    msgs = final_state.get("messages", [])
    if msgs:
        cover_note = getattr(msgs[-1], "content", "") or ""

    CONSOLE.print()
    CONSOLE.print(Rule())
    if cover_note:
        CONSOLE.print(Panel(_short(cover_note, 600), title="Cover note", border_style="green"))
    CONSOLE.print(f"  Duration   : {elapsed:.1f}s")
    CONSOLE.print(f"  VFS files  : {len(files)}  ({', '.join(sorted(files)) or 'none'})")
    if report_path:
        CONSOLE.print(f"  Report     : [bold]{report_path}[/bold]")
        CONSOLE.print(f"  [dim]open {report_path}[/dim]")
    elif files:
        CONSOLE.print(f"  [yellow]No report.md produced — saved {len(files)} other file(s) to {out_dir}[/yellow]")
    else:
        CONSOLE.print("  [yellow]No virtual files captured — see the cover note above.[/yellow]")
    CONSOLE.print(Rule())
    CONSOLE.print()


if __name__ == "__main__":
    main()

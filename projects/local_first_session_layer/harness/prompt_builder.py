"""
Prompt builder — assembles the two layers of memory into one prompt.

Two kinds of memory, two injection paths:

- Procedural memory (SKILL.md) — DETERMINISTIC. The same content is injected
  verbatim on every single session. This is the agent's "how I do my job"
  knowledge: output format, mandatory rules, known environment facts. It never
  varies, so it never surprises you.

- Declarative memory (Mem0 facts) — PROBABILISTIC. Facts surfaced by vector
  similarity against the current query. What comes back depends on the
  embedding model and what's in the store, so this path is where the
  interesting failure modes live (wrong fact retrieved, vocabulary gap).
"""

from pathlib import Path

# Resolve relative to this file so it works regardless of the caller's cwd.
SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def build_system_prompt(base_prompt: str, skill_files: list[str] | None = None) -> str:
    """Inject procedural memory (SKILL.md files) into the system prompt."""
    skill_files = skill_files or ["compliance_report_format.md"]
    procedural_blocks = []

    for filename in skill_files:
        skill_path = SKILLS_DIR / filename
        if skill_path.exists():
            content = skill_path.read_text()
            procedural_blocks.append(f"## Procedural Knowledge\n\n{content}")

    procedural_section = "\n\n---\n\n".join(procedural_blocks)
    return f"{procedural_section}\n\n---\n\n{base_prompt}"


def inject_declarative_memory(prompt: str, facts: list[dict]) -> str:
    """Inject retrieved Mem0 facts into the prompt."""
    if not facts:
        return prompt

    fact_lines = "\n".join(
        f"- {f['memory']} (session: {f.get('metadata', {}).get('session_id', 'unknown')})"
        for f in facts
    )
    memory_block = f"## Remembered from Previous Sessions\n\n{fact_lines}"
    return f"{memory_block}\n\n---\n\n{prompt}"

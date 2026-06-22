"""
Custom tools for the deep research agent.

deepagents gives us the *harness* tools for free (planning via `write_todos`,
the virtual filesystem via `read_file`/`write_file`/`edit_file`, and subagent
delegation via `task`). What it does NOT give us is a way to reach the outside
world — that is our job. The single capability we add here is web search.

We use DuckDuckGo (via the `ddgs` package) so there is **no API key to set up** —
just `pip install ddgs` and it works. This mirrors the harness philosophy from
the rest of agent_harness: the harness owns structure and enforcement; we supply
the domain tool.
"""
from typing import Literal


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
) -> list[dict]:
    """Run a web search and return trimmed results.

    Use this to gather information for a research question. Prefer several
    narrow queries over one broad query. Set `topic="news"` for current
    events; "general"/"finance" both do a normal web search.

    Args:
        query: The search query.
        max_results: How many results to return (1-10).
        topic: "news" uses the news index; otherwise a general web search.

    Returns:
        A list of {title, url, content} dicts. `content` is a snippet.
    """
    try:
        from ddgs import DDGS  # current package name
    except ImportError:  # pragma: no cover - older installs
        try:
            from duckduckgo_search import DDGS  # legacy name
        except ImportError:
            return [{
                "title": "SEARCH UNAVAILABLE",
                "url": "",
                "content": (
                    "The 'ddgs' package is not installed. Tell the user to run "
                    "`pip install ddgs` and do not fabricate results."
                ),
            }]

    n = max(1, min(max_results, 10))
    try:
        with DDGS() as ddgs:
            if topic == "news":
                raw = ddgs.news(query, max_results=n)
            else:
                raw = ddgs.text(query, max_results=n)
    except Exception as exc:  # rate limits, transient network errors, etc.
        return [{
            "title": "SEARCH ERROR",
            "url": "",
            "content": (
                f"Web search failed ({type(exc).__name__}: {exc}). Report this "
                "honestly; do not invent sources. A retry may succeed."
            ),
        }]

    # Normalize both .text() ({title, href, body}) and .news()
    # ({title, url, body, date, source}) into one shape, trimmed to keep each
    # subagent's isolated context clean and token-cheap.
    results = []
    for r in raw or []:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("href") or r.get("url", ""),
            "content": (r.get("body") or "")[:2000],
        })
    return results or [{
        "title": "NO RESULTS",
        "url": "",
        "content": f"No results for query: {query!r}. Try rephrasing.",
    }]

"""
Synthetic RAG payload that mimics real agentic workload bloat:
  - JSON tool output (SmartCrusher target)
  - Code search results (CodeCompressor target)
  - Prose document chunks (Kompress-base target)
Designed to be chunky enough to show meaningful compression deltas.
"""

TOOL_OUTPUT_JSON = """
[
  {"id": "usr_001", "name": "Alice Chen", "role": "engineer", "team": "platform", "email": "alice@example.com", "slack": "@alice", "timezone": "America/Toronto", "created_at": "2023-01-15T09:00:00Z", "updated_at": "2024-11-02T14:32:11Z", "status": "active", "permissions": ["read", "write", "deploy"], "metadata": {"hire_date": "2023-01-10", "manager": "Bob Patel", "cost_center": "ENG-01", "seat_license": "pro"}},
  {"id": "usr_002", "name": "Bob Patel", "role": "manager", "team": "platform", "email": "bob@example.com", "slack": "@bob", "timezone": "America/Toronto", "created_at": "2022-06-01T08:00:00Z", "updated_at": "2024-10-30T10:01:44Z", "status": "active", "permissions": ["read", "write", "deploy", "admin"], "metadata": {"hire_date": "2022-05-28", "manager": "Carol Wu", "cost_center": "ENG-01", "seat_license": "enterprise"}},
  {"id": "usr_003", "name": "Diana Ross", "role": "engineer", "team": "data", "email": "diana@example.com", "slack": "@diana", "timezone": "America/Vancouver", "created_at": "2023-07-20T11:00:00Z", "updated_at": "2024-11-01T08:55:30Z", "status": "active", "permissions": ["read", "write"], "metadata": {"hire_date": "2023-07-15", "manager": "Eve Kim", "cost_center": "DATA-02", "seat_license": "pro"}},
  {"id": "usr_004", "name": "Eve Kim", "role": "manager", "team": "data", "email": "eve@example.com", "slack": "@eve", "timezone": "America/Vancouver", "created_at": "2021-03-10T09:30:00Z", "updated_at": "2024-11-03T16:12:00Z", "status": "active", "permissions": ["read", "write", "deploy", "admin"], "metadata": {"hire_date": "2021-03-08", "manager": "Frank Liu", "cost_center": "DATA-02", "seat_license": "enterprise"}},
  {"id": "usr_005", "name": "Frank Liu", "role": "vp", "team": "engineering", "email": "frank@example.com", "slack": "@frank", "timezone": "America/New_York", "created_at": "2019-08-01T07:00:00Z", "updated_at": "2024-11-04T12:00:00Z", "status": "active", "permissions": ["read", "write", "deploy", "admin", "billing"], "metadata": {"hire_date": "2019-07-28", "manager": "CEO", "cost_center": "ENG-00", "seat_license": "enterprise"}},
  {"id": "usr_006", "name": "Grace Zhao", "role": "engineer", "team": "security", "email": "grace@example.com", "slack": "@grace", "timezone": "America/Chicago", "created_at": "2024-02-12T10:00:00Z", "updated_at": "2024-10-28T09:00:00Z", "status": "active", "permissions": ["read", "write", "security_audit"], "metadata": {"hire_date": "2024-02-10", "manager": "Hiro Tanaka", "cost_center": "SEC-03", "seat_license": "pro"}},
  {"id": "usr_007", "name": "Hiro Tanaka", "role": "manager", "team": "security", "email": "hiro@example.com", "slack": "@hiro", "timezone": "America/Chicago", "created_at": "2020-11-15T08:45:00Z", "updated_at": "2024-11-02T15:30:00Z", "status": "active", "permissions": ["read", "write", "deploy", "admin", "security_audit"], "metadata": {"hire_date": "2020-11-12", "manager": "Frank Liu", "cost_center": "SEC-03", "seat_license": "enterprise"}},
  {"id": "usr_008", "name": "Iris Novak", "role": "engineer", "team": "platform", "email": "iris@example.com", "slack": "@iris", "timezone": "America/Toronto", "created_at": "2023-09-05T09:00:00Z", "updated_at": "2024-10-31T11:20:00Z", "status": "active", "permissions": ["read", "write"], "metadata": {"hire_date": "2023-09-01", "manager": "Bob Patel", "cost_center": "ENG-01", "seat_license": "pro"}},
  {"id": "usr_009", "name": "James Carter", "role": "engineer", "team": "data", "email": "james@example.com", "slack": "@james", "timezone": "America/Los_Angeles", "created_at": "2022-04-18T10:30:00Z", "updated_at": "2024-11-01T14:05:00Z", "status": "inactive", "permissions": ["read"], "metadata": {"hire_date": "2022-04-15", "manager": "Eve Kim", "cost_center": "DATA-02", "seat_license": "basic"}},
  {"id": "usr_010", "name": "Karen Lee", "role": "engineer", "team": "platform", "email": "karen@example.com", "slack": "@karen", "timezone": "America/Toronto", "created_at": "2024-05-01T08:00:00Z", "updated_at": "2024-11-03T10:00:00Z", "status": "active", "permissions": ["read", "write", "deploy"], "metadata": {"hire_date": "2024-04-29", "manager": "Bob Patel", "cost_center": "ENG-01", "seat_license": "pro"}}
]
"""

CODE_SEARCH_RESULTS = """
=== grep -r "def compress" ./headroom --include="*.py" ===

headroom/core/compress.py:12:def compress(messages: list[dict], model: str = "claude-3-5-sonnet-20241022", **kwargs) -> list[dict]:
headroom/core/compress.py:47:def compress_single(content: str, content_type: str | None = None) -> CompressionResult:
headroom/core/compress.py:89:def compress_with_cache(messages: list[dict], cache_key: str | None = None) -> tuple[list[dict], CacheStats]:

headroom/compressors/json_compressor.py:8:def compress(obj: dict | list, *, max_depth: int = 4, strip_nulls: bool = True) -> str:
headroom/compressors/json_compressor.py:34:def compress_array(arr: list[dict]) -> str:
headroom/compressors/json_compressor.py:56:def compress_homogeneous(arr: list[dict], schema: dict) -> str:

headroom/compressors/code_compressor.py:11:def compress(source: str, language: str, *, keep_docstrings: bool = False) -> str:
headroom/compressors/code_compressor.py:44:def compress_python(tree: ast.AST, keep_docstrings: bool) -> str:
headroom/compressors/code_compressor.py:81:def compress_javascript(source: str) -> str:

headroom/compressors/prose_compressor.py:15:def compress(text: str, *, ratio: float = 0.4, model_path: str | None = None) -> str:
headroom/compressors/prose_compressor.py:62:def compress_batch(texts: list[str], ratio: float = 0.4) -> list[str]:

headroom/proxy/middleware.py:22:def compress_request(scope: dict, receive: Callable, send: Callable) -> None:
headroom/proxy/middleware.py:55:def compress_response_stream(response_body: bytes) -> bytes:

headroom/cache/ccr.py:19:def compress_and_cache(content: str, content_id: str, ttl: int = 3600) -> CachedContent:
headroom/cache/ccr.py:48:def retrieve(content_id: str) -> str | None:

=== headroom/core/compress.py (lines 1-90) ===

import json
from typing import Any
from headroom.compressors.router import ContentRouter
from headroom.cache.aligner import CacheAligner
from headroom.cache.ccr import CCRCache
from headroom.models import CompressionResult, CacheStats
from headroom.providers.registry import get_provider

_router = ContentRouter()
_aligner = CacheAligner()
_ccr = CCRCache()


def compress(messages: list[dict], model: str = "claude-3-5-sonnet-20241022", **kwargs) -> list[dict]:
    \"\"\"
    Compress a messages list before sending to an LLM.
    Modifies tool_result and user message content in-place via router dispatch.
    Returns new list; originals cached in CCR with content_id references.
    \"\"\"
    provider = get_provider(model)
    compressed = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(content, list):
            new_content = []
            for block in content:
                if block.get("type") == "tool_result":
                    result = _compress_block(block, provider)
                    new_content.append(result)
                elif block.get("type") == "text":
                    result = _router.route_and_compress(block["text"])
                    new_content.append({"type": "text", "text": result.compressed})
                else:
                    new_content.append(block)
            compressed.append({**msg, "content": new_content})
        elif isinstance(content, str) and role == "user":
            result = _router.route_and_compress(content)
            compressed.append({**msg, "content": result.compressed})
        else:
            compressed.append(msg)
    return _aligner.align(compressed, model=model)


def compress_single(content: str, content_type: str | None = None) -> CompressionResult:
    \"\"\"
    Compress a single blob. content_type hints the router; if None, auto-detects.
    \"\"\"
    return _router.route_and_compress(content, hint=content_type)


def compress_with_cache(messages: list[dict], cache_key: str | None = None) -> tuple[list[dict], CacheStats]:
    \"\"\"
    Compress + return CCR cache statistics for before/after comparison.
    \"\"\"
    stats_before = _ccr.stats()
    compressed = compress(messages)
    stats_after = _ccr.stats()
    delta = CacheStats(
        entries_added=stats_after.total_entries - stats_before.total_entries,
        bytes_cached=stats_after.total_bytes - stats_before.total_bytes,
    )
    return compressed, delta
"""

PROSE_CHUNK_1 = """
Context compression in agentic AI systems addresses a fundamental inefficiency: language models consume tokens proportionally to input size, but most of that input is structural ceremony rather than semantic signal. When an agent executes a grep command over a large codebase, the raw output might contain hundreds of matching lines with full file paths, line numbers, and surrounding context — yet the actionable information is typically a handful of function signatures or variable names. The model reads (and pays for) all of it.

The naive mitigation is truncation: cut the output at N tokens. But truncation is brittle; the most relevant line might be the last one. Summarization via a secondary LLM call avoids this brittleness at the cost of latency and doubled inference spend. Neither approach preserves the original for retrieval if the model determines mid-reasoning that it actually needed that truncated section.

Reversible compression, as implemented in systems like Headroom, takes a third path. Content is compressed by type-aware algorithms (AST-aware for code, schema-normalized for JSON, extractive for prose) and the original is cached locally with a content identifier that the model can use to request retrieval. The model operates on the cheap version by default; the expensive original persists on disk with a configurable TTL. This changes the economics: you pay for compressed tokens always, and full tokens only when the model decides it needs them — which, in practice, is rare for routine tool outputs.

The architectural insight is that this is a pipeline concern, not a prompt concern. It belongs in the harness layer that routes messages, not in the system prompt that instructs the model. Models don't reliably self-compress; they do reliably call tools. Treating "retrieve full content" as a standard tool invocation makes the pattern composable with any agent framework.
"""

PROSE_CHUNK_2 = """
Prompt cache preservation is the non-obvious constraint that shapes how context compression must be implemented. Provider KV caches (Anthropic's, OpenAI's) hash the exact byte sequence of the prompt prefix to determine a cache hit. Naive compression — even semantically lossless compression — changes that byte sequence, so every compressed call is a cache miss. In workloads where the system prompt and static context dominate token spend, this can make compression a net loss: you save input tokens on the compressed portion but lose the cache discount on the static portion.

The correct implementation separates stable content (system prompt, static RAG corpus, conversation history that has stabilized) from volatile content (new tool outputs, fresh user messages). The stable portion must be bit-for-bit identical across turns for the cache to hit. Only the volatile portion should be compressed. A CacheAligner component that explicitly partitions messages and stabilizes prefix bytes resolves this — but it requires knowing the provider's caching boundary, which differs between Anthropic (explicit cache_control markers) and OpenAI (automatic on prefixes above a threshold).

The practical implication: don't measure compression savings in isolation. Measure net token cost including cache hit delta. A 60% input token reduction that causes a 40% cache miss rate increase may be roughly break-even on cost while adding latency. The valid experiment is: run the proxy against one production call path, measure (a) raw input tokens, (b) cache hit rate, and (c) effective billed tokens = uncached_input_tokens + (cached_tokens * cache_rate), before and after. That's the number that matters.
"""


def build_rag_messages(user_query: str) -> list[dict]:
    """
    Build messages in agentic tool_result format so headroom can route
    each content block to the correct compressor:
      - JSON tool output → tool_result block → SmartCrusher
      - Code search      → tool_result block → CodeCompressor
      - Prose chunks     → text blocks       → Kompress-base
    """
    system_prompt = (
        "You are a senior platform engineer assistant. "
        "Answer questions using the retrieved context below. "
        "Be precise and cite specific details from the context."
    )

    # Simulate a prior assistant turn that called retrieval tools,
    # then a user turn with the tool results — this is the pattern headroom is built for.
    messages = [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool_json_001",
                    "name": "user_service_lookup",
                    "input": {"filter": "team=platform,data,security"},
                },
                {
                    "type": "tool_use",
                    "id": "tool_code_002",
                    "name": "code_search",
                    "input": {"query": "def compress", "repo": "headroom"},
                },
                {
                    "type": "tool_use",
                    "id": "tool_doc_003",
                    "name": "doc_retriever",
                    "input": {"query": "context compression agentic", "top_k": 2},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                # JSON tool result — SmartCrusher strips redundant keys from homogeneous array
                # headroom requires string content (not nested list) to route to compressors
                {
                    "type": "tool_result",
                    "tool_use_id": "tool_json_001",
                    "content": TOOL_OUTPUT_JSON.strip(),
                },
                # Code search result — CodeCompressor applies AST-aware reduction
                {
                    "type": "tool_result",
                    "tool_use_id": "tool_code_002",
                    "content": CODE_SEARCH_RESULTS.strip(),
                },
                # Prose doc chunks — Kompress-base extractive compression
                {
                    "type": "tool_result",
                    "tool_use_id": "tool_doc_003",
                    "content": (PROSE_CHUNK_1 + "\n\n" + PROSE_CHUNK_2).strip(),
                },
                # The actual user question — NOT compressed (protected by headroom)
                {
                    "type": "text",
                    "text": user_query,
                },
            ],
        },
    ]

    return messages, system_prompt

"""
LangGraph pipeline for the compression experiment.

Two graphs are exported:
  baseline_graph   — retrieve → generate  (no compression)
  compressed_graph — retrieve → compress → generate

Both graphs share the same state shape and node implementations;
the only difference is whether the compress node is wired in.
"""

import time
from typing import TypedDict, Annotated
import operator

import tiktoken
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from projects.local_first_compression_layer.config import MODEL, OLLAMA_BASE_URL, SYSTEM_PROMPT, USER_QUERY
from projects.local_first_compression_layer.data.sample_rag_chunks import build_rag_messages

# tiktoken cl100k_base is a reasonable approximation across Qwen/DeepSeek tokenizers
_enc = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def _messages_token_count(messages: list[dict]) -> int:
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += _count_tokens(content)
        elif isinstance(content, list):
            for block in content:
                btype = block.get("type", "")
                if btype == "text" and "text" in block:
                    total += _count_tokens(block["text"])
                elif btype == "tool_result":
                    inner = block.get("content", "")
                    if isinstance(inner, str):
                        total += _count_tokens(inner)
                    elif isinstance(inner, list):
                        for item in inner:
                            if isinstance(item, dict) and "text" in item:
                                total += _count_tokens(item["text"])
    return total


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    # raw messages dict list (OpenAI-wire format for headroom compat)
    raw_messages: list[dict]
    system_prompt: str
    # messages that go to the model (may be compressed or raw)
    send_messages: list[dict]
    # metrics — headroom-reported (exact) when compression is on, tiktoken (approx) otherwise
    raw_token_estimate: int
    send_token_estimate: int
    tokens_saved: int
    compression_ratio: float
    transforms_applied: list[str]
    compression_applied: bool
    inference_time_s: float
    prompt_tokens: int       # from Ollama response usage
    completion_tokens: int
    answer: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def retrieve_node(state: AgentState) -> AgentState:
    """Build the RAG-heavy messages list from sample data."""
    messages, system = build_rag_messages(USER_QUERY)
    raw_estimate = _messages_token_count(messages)
    return {
        **state,
        "raw_messages": messages,
        "system_prompt": system,
        "send_messages": messages,          # default: send raw
        "raw_token_estimate": raw_estimate,
        "send_token_estimate": raw_estimate,
        "tokens_saved": 0,
        "compression_ratio": 1.0,
        "transforms_applied": [],
        "compression_applied": False,
    }


def compress_node(state: AgentState) -> AgentState:
    """
    Apply headroom compress() to reduce message size before sending.
    Uses CompressResult fields directly — more accurate than tiktoken re-estimation.
    Falls back to raw messages if headroom fails.
    """
    try:
        from headroom import compress as hd_compress
        result = hd_compress(
            state["raw_messages"],
            model="gpt-4o",
            compress_user_messages=True,  # RAG tool results live in user messages
            protect_recent=0,             # compress all turns, not just history
            kompress_model="disabled",    # no HF/ONNX model — only SmartCrusher (JSON) + CodeCompressor (AST)
        )
        return {
            **state,
            "send_messages": result.messages,
            "send_token_estimate": result.tokens_after,
            "raw_token_estimate": result.tokens_before,
            "tokens_saved": result.tokens_saved,
            "compression_ratio": result.compression_ratio,
            "transforms_applied": list(result.transforms_applied or []),
            "compression_applied": True,
        }
    except Exception as exc:
        print(f"[headroom] compress() failed ({exc}), sending raw messages")
        return {**state, "compression_applied": False}


def _flatten_content(content) -> str:
    """
    Convert OpenAI/Anthropic content (string or list of blocks) to plain text
    for Ollama, which doesn't understand tool_result/tool_use blocks natively.
    """
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        btype = block.get("type", "")
        if btype == "text":
            parts.append(block["text"])
        elif btype == "tool_result":
            inner = block.get("content", "")
            if isinstance(inner, str):
                parts.append(inner)
            elif isinstance(inner, list):
                for item in inner:
                    if isinstance(item, dict):
                        parts.append(item.get("text", ""))
                    else:
                        parts.append(str(item))
        elif btype == "tool_use":
            # skip tool_use blocks — they describe calls, not content
            pass
    return "\n\n".join(p for p in parts if p)


def generate_node(state: AgentState) -> AgentState:
    """
    Send messages to local Ollama model and capture usage + timing.
    Flattens tool_result content blocks to plain text since Ollama doesn't
    natively support the Anthropic tool_result message format.
    """
    llm = ChatOllama(
        model=MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
    )

    lc_messages = [SystemMessage(content=state["system_prompt"])]
    for m in state["send_messages"]:
        role = m.get("role", "user")
        flat = _flatten_content(m.get("content", ""))
        if not flat:
            continue
        if role == "user":
            lc_messages.append(HumanMessage(content=flat))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=flat))

    t0 = time.perf_counter()
    response = llm.invoke(lc_messages)
    elapsed = time.perf_counter() - t0

    meta = response.response_metadata or {}
    usage = meta.get("prompt_eval_count", 0), meta.get("eval_count", 0)

    return {
        **state,
        "inference_time_s": round(elapsed, 2),
        "prompt_tokens": usage[0],
        "completion_tokens": usage[1],
        "answer": response.content,
    }


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------

def _build_graph(with_compression: bool) -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)

    if with_compression:
        g.add_node("compress", compress_node)
        g.set_entry_point("retrieve")
        g.add_edge("retrieve", "compress")
        g.add_edge("compress", "generate")
    else:
        g.set_entry_point("retrieve")
        g.add_edge("retrieve", "generate")

    g.add_edge("generate", END)
    return g.compile()


baseline_graph   = _build_graph(with_compression=False)
compressed_graph = _build_graph(with_compression=True)


def run(with_compression: bool = False) -> AgentState:
    graph = compressed_graph if with_compression else baseline_graph
    initial: AgentState = {
        "raw_messages": [],
        "system_prompt": "",
        "send_messages": [],
        "raw_token_estimate": 0,
        "send_token_estimate": 0,
        "tokens_saved": 0,
        "compression_ratio": 1.0,
        "transforms_applied": [],
        "compression_applied": False,
        "inference_time_s": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "answer": "",
    }
    return graph.invoke(initial)

from langchain_ollama import ChatOllama
from langchain.agents import create_agent as create_react_agent
from langchain_core.messages import HumanMessage
from config import OLLAMA_MODEL, OLLAMA_BASE_URL
from shell_tools import bash_raw, bash_rtk, raw_tracker, rtk_tracker, rtk_available


def run_agent(task: str, mode: str = "raw") -> dict:
    if mode == "rtk" and not rtk_available():
        raise RuntimeError("RTK not installed. Run: brew install rtk")

    tracker = raw_tracker if mode == "raw" else rtk_tracker
    tracker.reset()

    llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    tool = bash_raw if mode == "raw" else bash_rtk
    graph = create_react_agent(llm, tools=[tool])

    result = graph.invoke({"messages": [HumanMessage(content=task)]})
    final = result["messages"][-1].content

    return {
        "mode": mode,
        "response": final,
        "tool_calls": len(tracker.records),
        "total_tool_tokens": tracker.total_tokens,
        "records": list(tracker.records),
    }

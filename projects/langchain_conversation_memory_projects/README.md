# langchain_conversation_memory_projects

Four side-by-side scripts comparing LangChain's built-in **conversation memory** types. Each script wires the memory class into a `ConversationChain` over an OpenAI LLM (`gpt-4`) and runs a sample `predict` so you can observe what the chain remembers.

## Files

| File | Memory class | Behavior |
|------|--------------|----------|
| `conversation_buffer_memory.py` | `ConversationBufferMemory` | Keeps the **entire** conversation verbatim. |
| `conversation_buffer_window_memory.py` | `ConversationBufferWindowMemory(k=2)` | Keeps only the last `k` interactions. |
| `conversation_summary_memory.py` | `ConversationSummaryMemory` | Continuously summarizes the conversation using a second LLM call. |
| `conversation_summary_buffer_memory.py` | `ConversationSummaryBufferMemory` | Hybrid: keeps the recent window verbatim AND summarizes older turns. |

## Prerequisites

- Python 3.9+
- An `OPENAI_API_KEY` exported in your environment:

  ```bash
  export OPENAI_API_KEY=sk-...
  ```

## Install

```bash
pip install -r requirements.txt
```

## Run

Each script is independent — run whichever memory type you want to inspect:

```bash
python conversation_buffer_memory.py
python conversation_buffer_window_memory.py
python conversation_summary_memory.py
python conversation_summary_buffer_memory.py
```

Each script sets `verbose=True`, so you'll see the chain's internal prompt (including the memory it injects) printed to stdout.

## Notes

These use the legacy `langchain.chains.conversation.memory` and `langchain.llms.openai` imports. They work, but for newer LangChain versions, equivalent APIs live under `langchain_community` / `langchain_openai`.

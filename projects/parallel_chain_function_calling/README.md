# parallel_chain_function_calling

Reference pattern for a **parallel, self-correcting LangChain tool-calling chain** fronted by a FastAPI service. The chain:

1. Sends the user input to an OpenAI-compatible model with tools bound (`model.bind_tools(tools)`).
2. Parses the tool call, dispatches it via `RunnableLambda(...).with_retry(...)`.
3. If the tool raises, falls back through `handle_exception` and re-prompts the model with the error so it can retry with corrected arguments (`self_correcting_chain = parallel_chain.with_fallbacks([...])`).
4. The FastAPI `/message/` endpoint invokes the chain; on failure it falls back to a `default_chain`.

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app exposing `GET /` and `POST /message/`. |
| `parallel_chain.py` | The core `parallel_chain` and `self_correcting_chain` definitions. |
| `default_chain.py` | Fallback chain used when `parallel_chain` raises. |
| `model.py` | `ChatOpenAI` model construction, reading credentials from `common.config.Config`. |
| `exception.py` | `CustomToolException` carrying the failed tool call and the underlying exception. |

## Prerequisites

- Python 3.10+
- An OpenAI-compatible endpoint and API key, exposed via a `common.config.Config` module that provides `config.openai.token` and `config.openai.openai_api`.
- A `tools` module exporting an iterable of LangChain tools (referenced as `from tools import tools` in `parallel_chain.py`).

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

Then:

```bash
curl -X POST http://localhost:8000/message/ \
  -H "Content-Type: application/json" \
  -d '{"text": "hello", "response": null}'
```

## Notes

This folder is a **pattern reference**, not a fully runnable project on its own — `common.config`, `tools`, and the `Message` model are expected to be supplied by the host application. Treat it as a template you copy into a larger codebase.

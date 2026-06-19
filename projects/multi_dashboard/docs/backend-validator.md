# Validator Backend — SSE Streaming Demo

**Port:** 8002 | **Stack:** FastAPI (stateless)

Demonstrates Server-Sent Events (SSE) — a technique for streaming data from the server to the browser. Simulates validating network device configurations and streaming results back in real time.

**API docs:** http://localhost:8002/docs

---

## What You'll Learn

- What Server-Sent Events (SSE) are and when to use them
- How to write a streaming endpoint in FastAPI using `StreamingResponse` and async generators
- The SSE wire format (`event: ...\ndata: ...\n\n`)
- Why SSE is simpler than WebSocket for one-way streaming
- Progressive UI updates — showing results as they arrive instead of waiting

---

## SSE vs WebSocket — Which Should You Use?

| | SSE | WebSocket |
|-|-----|-----------|
| Direction | Server → Client only | Both directions |
| Protocol | Plain HTTP | Upgraded HTTP (ws://) |
| Browser support | `EventSource` API or `fetch()` | `WebSocket` API |
| Reconnect | Automatic | Manual |
| Use when | Streaming results, live feeds | Chat, collaborative editing |

**This service uses SSE** because validation results only flow in one direction (server → browser).

---

## How SSE Works

The server sends a continuous stream of text over a single HTTP connection:

```
event: progress
data: {"percent": 25, "message": "Checking interface config..."}

event: progress
data: {"percent": 50, "message": "Validating routing table..."}

event: result
data: {"device": "router-1", "status": "pass", "issues": []}

event: done
data: {}
```

Each "event block" is separated by a blank line. The browser reads these as they arrive.

---

## Project Structure

```
backends/validator-py/
└── app/
    ├── main.py          # App factory
    └── routers/
        ├── validate.py  # Sync validation endpoint
        └── stream.py    # SSE streaming endpoint
```

---

## The Streaming Endpoint

```python
@app.get("/stream/{device_id}")
async def stream_validation(device_id: str):
    async def event_generator():
        # Yield SSE-formatted strings
        yield f"event: progress\ndata: {json.dumps({'percent': 25})}\n\n"
        await asyncio.sleep(1)   # simulates work
        yield f"event: result\ndata: {json.dumps({'status': 'pass'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

The key parts:
1. The function is an **async generator** (uses `yield` instead of `return`)
2. `StreamingResponse` wraps it and keeps the HTTP connection open
3. `media_type="text/event-stream"` tells the browser it's SSE

---

## Try It

```bash
# Stream validation results (watch them arrive one by one)
curl -N http://localhost:8002/stream/device-001
```

The `-N` flag disables curl's output buffering so you see events as they arrive.

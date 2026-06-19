# SSE (Server-Sent Events) — Streaming Guide

This guide explains how Server-Sent Events work and how they're used in the validator and chatbot services.

---

## What Is SSE?

SSE is a simple way for a server to stream data to a browser over a regular HTTP connection. The connection stays open, and the server pushes events as they become available.

```
Client makes one HTTP request
Server keeps the connection open
Server sends events whenever it has data
Client receives events as they arrive (no polling)
```

---

## SSE vs WebSocket vs Polling

| | SSE | WebSocket | REST Polling |
|-|-----|-----------|--------------|
| Direction | Server → Client | Both ways | Client asks repeatedly |
| Protocol | HTTP | ws:// | HTTP |
| Reconnect | Automatic | Manual | N/A |
| Best for | Live feeds, streaming AI | Chat, games | Simple async jobs |

**Choose SSE when:**
- You only need server → client data flow
- You want simplicity (it's just HTTP)
- You need automatic reconnection

---

## The SSE Wire Format

SSE is plain text over HTTP. Each event has an optional `event:` type and a `data:` field:

```
event: status
data: {"percent": 25, "message": "Checking..."}

event: result
data: {"device": "router-1", "passed": true}

event: done
data: {}

```

Events are separated by a **blank line**. The client reads these one at a time as they arrive.

---

## Python Implementation (FastAPI)

Use `StreamingResponse` with an async generator:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio, json

@app.get("/stream/{device_id}")
async def stream_results(device_id: str):
    async def generate():
        for percent in [25, 50, 75, 100]:
            data = {"percent": percent, "message": f"Checking step {percent}..."}
            yield f"event: progress\ndata: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.5)   # simulates work
        
        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

Key points:
- The generator uses `yield` not `return`
- Each event ends with `\n\n` (double newline)
- `media_type="text/event-stream"` tells the browser it's SSE

---

## Go Implementation (Fiber)

```go
func StreamHandler(c *fiber.Ctx) error {
    c.Set("Content-Type", "text/event-stream")
    c.Set("Cache-Control", "no-cache")
    c.Set("Connection", "keep-alive")

    c.Context().SetBodyStreamWriter(func(w *bufio.Writer) {
        for i := 25; i <= 100; i += 25 {
            fmt.Fprintf(w, "event: progress\ndata: {\"percent\": %d}\n\n", i)
            w.Flush()
            time.Sleep(500 * time.Millisecond)
        }
        fmt.Fprintf(w, "event: done\ndata: {}\n\n")
        w.Flush()
    })
    return nil
}
```

---

## Frontend — Reading SSE

Because SSE endpoints require custom auth headers, the chatbot frontend uses `fetch()` instead of the native `EventSource` API:

```typescript
const response = await fetch("http://localhost:8003/api/chat/stream", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,  // EventSource can't set this!
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ message }),
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  // Parse SSE lines and handle events
  for (const line of text.split("\n")) {
    if (line.startsWith("data: ")) {
      const data = JSON.parse(line.slice(6));
      // handle the event
    }
  }
}
```

**Why not `EventSource`?** The browser's native `EventSource` only supports GET requests and can't set custom headers. For authenticated SSE with POST bodies, use `fetch()` + `ReadableStream`.

---

## Testing SSE with curl

```bash
# The -N flag disables output buffering (you see events as they arrive)
curl -N http://localhost:8002/stream/device-001

# With auth (chatbot SSE)
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

curl -N -X POST http://localhost:8003/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

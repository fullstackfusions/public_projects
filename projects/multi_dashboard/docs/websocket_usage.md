# WebSocket — Real-Time Bidirectional Communication Guide

This guide explains how WebSocket works and how it's implemented in both the Python and Go chatbot services.

---

## What Is WebSocket?

WebSocket is a protocol that upgrades a regular HTTP connection into a persistent two-way channel. Once the connection is open, both the client and server can send messages at any time — without the client needing to ask first.

```
Regular HTTP:  Client asks → Server responds → connection closes → repeat
WebSocket:     Client connects → connection stays open → both sides send freely
```

---

## When to Use WebSocket vs SSE

| | WebSocket | SSE |
|-|-----------|-----|
| Direction | Two-way | Server → Client only |
| Complexity | Slightly higher | Simpler |
| Use when | Chat, games, live collaboration | Streaming results, live feeds |

WebSocket is used in the chatbot services because the client sends messages and the server responds — that's two-way.

---

## The Message Protocol

The chatbot services use JSON messages over WebSocket. Here's the full flow:

**Client sends:**
```json
{"message": "What's the capital of France?", "conversation_id": "optional-uuid"}
```

**Server sends (in order):**
```json
{"type": "received", "message_id": "uuid", "conversation_id": "uuid"}
{"type": "status", "status": "Thinking...", "progress": 30}
{"type": "status", "status": "Generating response...", "progress": 70}
{"type": "chunk", "content": "The capital"}
{"type": "chunk", "content": " of France is"}
{"type": "chunk", "content": " Paris."}
{"type": "complete", "conversation_id": "uuid"}
```

This word-by-word streaming is the same technique ChatGPT uses.

---

## Python Implementation (FastAPI)

```python
from fastapi import WebSocket

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Read message from client
            data = await websocket.receive_json()
            
            # Stream response back
            for word in response.split():
                await websocket.send_json({"type": "chunk", "content": word + " "})
                await asyncio.sleep(0.05)  # simulates streaming
            
            await websocket.send_json({"type": "complete"})
    except WebSocketDisconnect:
        pass  # client disconnected, clean up
```

---

## Go Implementation (Fiber + gorilla/websocket)

```go
app.Get("/ws/chat", websocket.New(func(c *websocket.Conn) {
    // Each connection runs in its own goroutine
    for {
        _, msg, err := c.ReadMessage()
        if err != nil {
            break  // client disconnected
        }
        
        // Stream response back word by word
        for _, word := range strings.Split(response, " ") {
            c.WriteJSON(map[string]string{"type": "chunk", "content": word})
            time.Sleep(50 * time.Millisecond)
        }
    }
}))
```

---

## WebSocket Auth — A Special Case

Browsers cannot set custom HTTP headers when opening a WebSocket connection. This means `Authorization: Bearer <token>` doesn't work.

**Solution:** Pass the token as a query parameter:
```
ws://localhost:8004/ws/chat?access_token=<jwt>
```

The Go auth middleware accepts both `Authorization: Bearer` headers AND `?access_token=` query params. The Python chatbot leaves WebSocket unauthenticated for simplicity (REST and SSE are auth-protected).

---

## Testing WebSocket

```bash
# Install wscat
npm install -g wscat

# Connect to Python chatbot (no auth)
wscat -c ws://localhost:8003/ws/chat

# Connect to Go chatbot (requires token)
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

wscat -c "ws://localhost:8004/ws/chat?access_token=$TOKEN"

# Once connected, type:
{"message": "Hello!"}
```

---

## Frontend Usage

The frontend uses the browser's native `WebSocket` API:

```typescript
const ws = new WebSocket(`ws://localhost:8003/ws/chat`);

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "chunk") {
    appendToChat(msg.content);
  }
};

ws.send(JSON.stringify({ message: "Hello!" }));
```

See `frontends/customer-portal/src/features/chat_py/` for the full React implementation.

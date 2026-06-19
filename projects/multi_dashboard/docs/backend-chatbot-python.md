# Chatbot Backend (Python) — Multi-Protocol Chat

**Port:** 8003 | **Stack:** FastAPI + WebSocket + SSE

Implements the same chat interface three different ways — WebSocket, Server-Sent Events, and REST with polling. The goal is to show you the tradeoffs between each approach.

**API docs:** http://localhost:8003/docs  
**WebSocket:** `ws://localhost:8003/ws/chat`

---

## What You'll Learn

- **WebSocket** — full-duplex (two-way) real-time communication
- **SSE** — one-way server-to-client streaming
- **REST + polling** — traditional async pattern (submit → check status)
- When to choose each approach
- In-memory conversation history (no database needed for demos)

---

## The Three Protocols Side by Side

### 1. WebSocket (`/ws/chat`)

The client and server both send and receive messages over one persistent connection.

```
Client opens ws://localhost:8003/ws/chat
  → client sends: {"message": "Hello"}
  ← server sends: {"type": "status", "status": "Thinking..."}
  ← server sends: {"type": "chunk", "content": "Hi "}
  ← server sends: {"type": "chunk", "content": "there!"}
  ← server sends: {"type": "complete"}
```

**Best for:** Chat apps, live collaboration, games — anything needing two-way real-time updates.

### 2. SSE (`POST /api/chat/stream`)

The client makes one HTTP request. The server keeps the connection open and streams the response.

```
Client POST /api/chat/stream  {"message": "Hello"}
  ← event: status  data: {"status": "Thinking..."}
  ← event: chunk   data: {"content": "Hi "}
  ← event: chunk   data: {"content": "there!"}
  ← event: done    data: {}
```

**Best for:** Streaming AI responses (like ChatGPT), live feeds, log streaming.

### 3. REST + Polling (`POST /api/chat/async` → `GET /api/chat/status/{id}`)

The client submits a request and gets back a job ID. Then it polls until done.

```
Client POST /api/chat/async   {"message": "Hello"}
  ← {"request_id": "abc123", "status": "pending"}

Client GET /api/chat/status/abc123
  ← {"status": "processing", "progress": 40}

Client GET /api/chat/status/abc123
  ← {"status": "complete", "response": "Hi there!"}
```

**Best for:** Long-running jobs where you don't need a persistent connection, or environments where WebSocket/SSE aren't supported.

---

## Project Structure

```
backends/chatbot-py/
└── app/
    ├── main.py       # App factory
    ├── domain.py     # Chat logic (response generation, delays)
    ├── store.py      # In-memory conversation history
    └── routers/
        ├── ws.py     # WebSocket handler
        ├── sse.py    # SSE streaming handler
        ├── chat.py   # REST (sync + async + polling)
        └── health.py
```

---

## Key Endpoints

| Method | Path | Protocol | Auth required |
|--------|------|----------|--------------|
| WS | `/ws/chat` | WebSocket | No (open for demo) |
| `POST` | `/api/chat/stream` | SSE | Yes |
| `POST` | `/api/chat/async` | REST | Yes |
| `GET` | `/api/chat/status/{id}` | REST | Yes |
| `GET` | `/api/conversations/{id}` | REST | Yes |
| `DELETE` | `/api/conversations/{id}` | REST | Yes |

---

## Try It — WebSocket

```bash
# Install wscat if you don't have it
npm install -g wscat

# Connect and chat
wscat -c ws://localhost:8003/ws/chat
# Type: {"message": "Hello!"}
```

## Try It — SSE

```bash
# Get a token first
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

# Stream a chat response
curl -N -X POST http://localhost:8003/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a joke"}'
```

---

## Compare with chatbot-go

The Go version (`chatbot-go`, port 8004) implements the exact same endpoints. Reading both implementations side-by-side is one of the best ways to see how Python and Go handle async I/O differently.

See [backend-chatbot-go.md](./backend-chatbot-go.md) for the Go version.

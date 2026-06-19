# Chatbot Backend (Go) — Multi-Protocol Chat

**Port:** 8004 | **Stack:** Go + Fiber + WebSocket + SSE

The same chat service as `chatbot-py`, but built in Go. All three protocols (WebSocket, SSE, REST) are implemented identically. Comparing the two is a great way to understand how Go and Python handle concurrency differently.

**WebSocket:** `ws://localhost:8004/ws/chat?access_token=<token>`

---

## What You'll Learn

- Building a REST/WebSocket/SSE server in Go with Fiber
- How goroutines handle concurrency (vs Python's asyncio)
- Why Go uses `?access_token=` for WebSocket auth (browsers can't set headers on WebSocket connections)
- Go project layout conventions (`cmd/`, `internal/`)
- `sync.Map` for thread-safe in-memory storage

---

## Python vs Go — Real Differences

| | chatbot-py (Python) | chatbot-go (Go) |
|-|--------------------|--------------------|
| Concurrency | `asyncio` (single-threaded event loop) | goroutines (true parallelism) |
| Memory per connection | ~50MB baseline | ~5MB baseline |
| WebSocket auth | Token not enforced (demo only) | JWT required (`?access_token=`) |
| Error handling | Exceptions | Multiple return values (`result, err`) |
| Type system | Dynamic + Pydantic runtime checks | Static compile-time checks |

**Why does WebSocket need `?access_token=`?** Browsers don't allow custom HTTP headers when opening a WebSocket connection. So the token is passed as a query parameter instead. The Go auth middleware accepts both `Authorization: Bearer` headers and the `?access_token=` query param.

---

## Project Structure

```
backends/chatbot-go/
├── cmd/server/main.go     # Entry point — wires everything together (~100 lines)
└── internal/
    ├── config/            # Settings from environment variables
    ├── handlers/          # HTTP/WebSocket/SSE handlers
    │   ├── websocket.go
    │   ├── sse.go
    │   └── rest.go
    ├── domain/            # Chat response generation logic
    ├── store/             # In-memory conversation history (sync.Map)
    └── models/            # Go structs for request/response
```

---

## Endpoints

All routes require a JWT. WebSocket uses `?access_token=<token>`, others use `Authorization: Bearer`.

| Method | Path | Protocol |
|--------|------|----------|
| WS | `/ws/chat?access_token=<token>` | WebSocket |
| `POST` | `/api/chat/stream` | SSE |
| `POST` | `/api/chat/async` | REST |
| `GET` | `/api/chat/status/{id}` | REST |
| `GET` | `/healthz` | Health check |

---

## Try It — WebSocket

```bash
# Get a token
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

# Connect with token in query string
wscat -c "ws://localhost:8004/ws/chat?access_token=$TOKEN"
# Type: {"message": "Hello from Go!"}
```

## Try It — SSE

```bash
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

curl -N -X POST http://localhost:8004/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

---

## Go Concurrency Pattern

Each WebSocket connection runs in its own goroutine. Go can handle thousands of concurrent connections with minimal memory because goroutines are much lighter than OS threads.

```go
app.Get("/ws/chat", websocket.New(func(c *websocket.Conn) {
    // This entire function runs in its own goroutine
    // Thousands of these can run simultaneously
    for {
        msg, err := c.ReadMessage()
        if err != nil { break }
        // process and respond
    }
}))
```

Compare this with Python's asyncio, where a single event loop handles all connections cooperatively.

# Chatbot Backend (Go)

**Port:** 8004 | Go + Fiber + WebSocket + SSE

The same multi-protocol chat service as `chatbot-py`, built in Go. Great for comparing how Python and Go handle async I/O, WebSocket connections, and SSE streaming.

---

## Endpoints

| Endpoint | Protocol | Notes |
|----------|----------|-------|
| `/ws/chat?access_token=<jwt>` | WebSocket | Token via query param (browser limitation) |
| `POST /api/chat/stream` | SSE | Auth: Bearer header |
| `POST /api/chat/async` | REST | Returns job ID |
| `GET /api/chat/status/:id` | REST | Poll for result |
| `GET /healthz` | HTTP | Health check |

---

## Run It

```bash
# With Docker
docker compose up chatbot-go-backend

# Locally
cd backends/chatbot-go
go run ./cmd/server
```

---

## Try WebSocket

```bash
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

wscat -c "ws://localhost:8004/ws/chat?access_token=$TOKEN"
# Then type: {"message": "Hello from Go!"}
```

---

## See Also

- [docs/backend-chatbot-go.md](../../docs/backend-chatbot-go.md) — full guide + Python vs Go comparison
- [backends/chatbot-py/](../chatbot-py/) — same service in Python

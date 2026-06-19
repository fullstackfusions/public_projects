# Chatbot Backend (Python)

**Port:** 8003 | FastAPI + WebSocket + SSE

Demonstrates the same chat feature implemented three different ways: WebSocket, Server-Sent Events, and REST with polling. Compare these approaches and see the tradeoffs.

---

## What's Demonstrated

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `/ws/chat` | WebSocket | Persistent two-way connection, word-by-word streaming |
| `/api/chat/stream` | SSE | One HTTP request, server streams the full response |
| `/api/chat/async` | REST | Returns a job ID immediately, client polls for result |
| `/api/chat/status/{id}` | REST | Check status of an async request |

---

## Run It

```bash
# With Docker
docker compose up chatbot-backend

# Locally (from project root)
cd backends/chatbot-py
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

---

## Try WebSocket

```bash
npm install -g wscat
wscat -c ws://localhost:8003/ws/chat
# Then type: {"message": "Hello!"}
```

## Try SSE

```bash
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

curl -N -X POST http://localhost:8003/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me something interesting"}'
```

---

## See Also

- [docs/backend-chatbot-python.md](../../docs/backend-chatbot-python.md) — full guide with protocol comparisons
- [docs/websocket_usage.md](../../docs/websocket_usage.md) — WebSocket deep-dive
- [docs/sse_usage.md](../../docs/sse_usage.md) — SSE deep-dive
- [backends/chatbot-go/](../chatbot-go/) — same service in Go

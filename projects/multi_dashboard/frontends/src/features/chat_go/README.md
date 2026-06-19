# Chat Feature (Go Backend)

This chat feature demonstrates three different communication patterns using the **Go backend**:

1. **WebSocket** - Real-time bidirectional communication using Fiber's WebSocket support
2. **REST API** - Traditional request/response with polling for status updates
3. **SSE (Server-Sent Events)** - One-way server-to-client streaming

## Backend

The Go backend runs on port **8004** and provides:

- `ws://localhost:8004/ws/chat` - WebSocket endpoint
- `POST /api/chat` - Synchronous REST endpoint
- `POST /api/chat/async` - Async REST endpoint (returns request_id)
- `GET /api/chat/status/:request_id` - Poll for async status
- `POST /api/chat/stream` - SSE streaming endpoint

## Running

```bash
# Start the Go backend
cd chatbot_app_go/backend
go run cmd/server/main.go

# Or with Docker
docker-compose up chatbot-go-backend
```

## Environment Variables

```env
VITE_CHAT_GO_API_URL=http://localhost:8004
VITE_CHAT_GO_WS_URL=ws://localhost:8004
```

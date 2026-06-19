# Frontend: Chat

Two chat interfaces that connect to the Python and Go backends respectively. Both offer the same three protocols (WebSocket, SSE, REST) so you can compare the user experience side-by-side.

---

## What You'll Learn

- Using the browser's native `WebSocket` API
- Streaming SSE responses with `fetch()` + `ReadableStream`
- Why you can't use `EventSource` for authenticated SSE (no custom headers)
- React custom hooks for managing connection state
- Switching between protocols in the same UI

---

## How Each Protocol Feels

| Protocol | User Experience | When it's best |
|----------|----------------|----------------|
| WebSocket | Instant word-by-word streaming | Chat apps, games |
| SSE | Word-by-word streaming over HTTP | AI responses, live feeds |
| REST polling | "Loading..." then full response | Simple integrations |

---

## File Structure

```
src/features/chat_py/     ← connects to port 8003 (Python)
├── ChatPage.tsx          # Main chat UI
├── useChat.ts            # Custom hook (WebSocket, SSE, REST logic)
└── components/           # Message list, input, status

src/features/chat_go/     ← connects to port 8004 (Go)
└── (same structure)

src/api/
├── chat_py.ts            # API functions for Python chatbot
└── chat_go.ts            # API functions for Go chatbot
```

---

## Key Code Pattern — SSE with fetch()

The native `EventSource` API can't set custom headers (no way to send a JWT). Instead, the frontend uses `fetch()` with a `ReadableStream`:

```typescript
const response = await fetch(`${API_BASE}/api/chat/stream`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ message }),
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  // parse SSE chunks and update the chat UI
}
```

---

## WebSocket Auth Difference

The Python chatbot's WebSocket is open (no auth required — demo only).

The Go chatbot requires a token, but browsers can't set headers on WebSocket connections. Instead, the token goes in the URL:

```typescript
// chat_go.ts
const ws = new WebSocket(`ws://localhost:8004/ws/chat?access_token=${token}`);
```

This is why `auth.RequireAuth` in the Go shared library accepts both `Authorization: Bearer` headers and `?access_token=` query parameters.

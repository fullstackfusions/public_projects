# shared-go — Shared Go Library

A reusable library for every Go backend in the project. The Go equivalent of `shared-py` — same concepts, same patterns, different language.

---

## How Services Use It

Each Go backend references this module with a `replace` directive (no version bumps during development):

```go
// backends/todo-go/go.mod
require github.com/mihirzz/chatbot-shared-go v0.0.0
replace github.com/mihirzz/chatbot-shared-go => ../../shared-go
```

---

## What's in It

| Package | What it does |
|---------|-------------|
| `shared/config` | Loads settings from environment variables |
| `shared/logging` | Structured JSON logging (zap) |
| `shared/errors` | Consistent JSON error responses (matches Python shape) |
| `shared/auth` | JWT verification + `RequireAuth()` Fiber middleware |
| `shared/middleware` | Request ID, access logging, panic recovery for Fiber |
| `shared/db/sql` | pgx/v5 connection pool factory |
| `shared/db/mongo` | MongoDB client factory |

---

## The RequireAuth Middleware

The auth middleware accepts JWT tokens two ways:
1. `Authorization: Bearer <token>` header — standard for REST
2. `?access_token=<token>` query parameter — needed for WebSocket (browsers can't set headers)

```go
// Mount auth middleware on a route group
api := app.Group("/api", auth.RequireAuth(settings.AuthSecretKey))
```

---

## JWT Compatibility

JWTs issued by `auth-py` (Python) are valid in `shared-go` (Go), and vice versa — both use HS256 with the same `AUTH_SECRET_KEY`. A user logged in through the React frontend can call both Python and Go backends with the same token.

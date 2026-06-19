# Todo Backend — Task Management (Go + Fiber)

**Port:** 8080 | **Stack:** Go + Fiber + PostgreSQL + golang-migrate

A REST CRUD API for managing todos. The same concept as `scheduler-py` but built in Go — good for comparing how the same patterns look in two different languages.

**Health check:** http://localhost:8080/healthz

---

## What You'll Learn

- Building a REST CRUD API in Go using the Fiber framework
- Connecting to PostgreSQL using `pgx` (Go's fast Postgres driver)
- Database migrations using `golang-migrate` (similar to Alembic but for Go)
- Structuring a Go project with `cmd/`, `internal/` layout
- How JWT auth works in Go (Bearer token validation)

---

## Python vs Go — Same Pattern, Different Language

This service does the same thing as `scheduler-py`. Comparing them shows you how:

| Concept | Python (scheduler-py) | Go (todo-go) |
|---------|----------------------|--------------|
| Web framework | FastAPI | Fiber |
| ORM / driver | SQLAlchemy | pgx (no ORM) |
| Migrations | Alembic | golang-migrate |
| Request validation | Pydantic | manual binding + errors |
| Async | `async/await` | goroutines |

---

## Project Structure

```
backends/todo-go/
├── cmd/server/main.go    # Entry point — wires everything together
├── migrations/           # SQL migration files (up + down)
│   ├── 0001_init.up.sql
│   └── 0001_init.down.sql
└── internal/
    ├── config/           # Settings from environment variables
    ├── repo/             # Database queries (raw SQL via pgx)
    ├── service/          # Business logic
    ├── handlers/         # HTTP handlers (Fiber)
    └── models/           # Go structs for todos
```

**Why `internal/`?** Go's `internal` package rule prevents code outside this module from importing these packages. It enforces clean boundaries in larger projects.

---

## Database Schema

`todos` table (created by the migration files):

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Server-generated |
| `title` | text | Required |
| `description` | text | Optional |
| `completed` | bool | Default `false` |
| `due_date` | timestamptz | Optional |
| `created_at` | timestamptz | Auto-set |
| `updated_at` | timestamptz | Auto-updated |

---

## Endpoints

All routes require a JWT (`Authorization: Bearer <token>`).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/todos` | List todos (filter with `?completed=true`) |
| `POST` | `/todos` | Create a todo |
| `GET` | `/todos/:id` | Get one todo |
| `PUT` | `/todos/:id` | Replace a todo |
| `PATCH` | `/todos/:id` | Partially update (e.g., toggle completed) |
| `DELETE` | `/todos/:id` | Delete a todo |
| `GET` | `/healthz` | Health check (also tests DB connection) |

---

## Try It

```bash
# Get a token first (from auth-py)
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

# Create a todo
curl -X POST http://localhost:8080/todos \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn Go", "description": "Build something with Fiber"}'

# List todos
curl http://localhost:8080/todos \
  -H "Authorization: Bearer $TOKEN"
```

---

## Understanding golang-migrate

Migrations are plain SQL files named with a version number:
```
0001_init.up.sql    ← applied going forward
0001_init.down.sql  ← applied when rolling back
```

The app runs migrations automatically on startup using `go:embed` to bundle the SQL files into the binary. No external tool needed at runtime.

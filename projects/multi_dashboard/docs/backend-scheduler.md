# Scheduler Backend — Calendar Events & Reminders

**Port:** 7001 (host) → 8000 (container) | **Stack:** FastAPI + PostgreSQL + Alembic

A REST API for managing calendar events and reminders. Demonstrates a standard Python CRUD service with a relational database.

**API docs:** http://localhost:7001/docs

---

## What You'll Learn

- Building a REST CRUD API with FastAPI
- Using SQLAlchemy (ORM) to interact with PostgreSQL
- Database migrations with Alembic — how schema changes are tracked and applied
- Async database sessions with `asyncpg`
- One-to-many relationships (an event has many reminders)
- Dependency injection with FastAPI's `Depends()`

---

## How It Works

The scheduler stores **events** (calendar entries with a start/end time) and **reminders** (notifications attached to events). The frontend displays these in a calendar view.

```
POST /events          → create an event
GET  /events          → list all events (with their reminders)
POST /events/{id}/reminders → add a reminder to an event
DELETE /events/{id}   → delete event (cascades to its reminders)
```

---

## Project Structure

```
backends/scheduler-py/
├── migrations/          # Alembic migration files (track schema changes)
└── app/
    ├── main.py          # App factory
    ├── models/event.py  # SQLAlchemy Event + Reminder models
    ├── schemas/         # Pydantic request/response shapes
    ├── crud/            # Database query functions
    └── routers/         # FastAPI route handlers
        ├── events.py
        └── reminders.py
```

---

## Database Schema

Two tables managed by Alembic:

**events**
| Column | Type | Notes |
|--------|------|-------|
| `id` | integer | Auto-increment primary key |
| `title` | varchar | Required |
| `description` | text | Optional |
| `start_time` | timestamptz | Indexed for fast queries |
| `end_time` | timestamptz | |
| `location` | varchar | Optional |

**reminders**
| Column | Type | Notes |
|--------|------|-------|
| `id` | integer | Auto-increment primary key |
| `message` | varchar | |
| `remind_at` | timestamptz | When to fire the reminder |
| `event_id` | integer | Foreign key → events.id (cascade delete) |

---

## Understanding Alembic Migrations

Alembic tracks every change to your database schema as a versioned migration file. This means you can:
- Apply changes to production without dropping tables
- Roll back a bad migration
- Share schema changes with teammates via git

```bash
# Create a new migration after changing a model
alembic revision --autogenerate -m "add location column"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

---

## Try It

```bash
# Create an event (requires auth token from auth-py)
curl -X POST http://localhost:7001/events \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Team Meeting", "start_time": "2026-07-01T10:00:00Z", "end_time": "2026-07-01T11:00:00Z"}'

# List all events
curl http://localhost:7001/events \
  -H "Authorization: Bearer <token>"
```

---

## Key Concepts to Explore

- **N+1 query problem**: The `reminders` relationship uses `lazy="selectin"` — this loads reminders in one additional query instead of one query per event. Try changing it to `lazy="select"` and watching the query count increase.
- **Cascade delete**: Deleting an event automatically deletes its reminders. This is set at the database level with `ON DELETE CASCADE`.
- **Async sessions**: The service uses `async with session` to avoid blocking the event loop during database queries.

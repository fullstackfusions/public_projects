# Fullstack Learning Hub

A hands-on monorepo for learning **full-stack microservices development**. Each backend service is designed to teach a specific real-world concept — REST APIs, real-time communication, event-driven architecture, authentication, and AI agent orchestration — all wired to a single React frontend.

> Built for software developers and co-op students who want to experiment with real patterns used in production systems.

---

## What You'll Learn

| Concept | Service | Technology |
|---------|---------|------------|
| REST CRUD + SQL (Python) | `scheduler-py` | FastAPI + PostgreSQL + Alembic |
| REST CRUD + SQL (Go) | `todo-go` | Go + Fiber + PostgreSQL |
| Stateless computation API | `finance-py` | FastAPI (no database) |
| Server-Sent Events (SSE) | `validator-py` | FastAPI streaming |
| WebSocket + SSE in Python | `chatbot-py` | FastAPI WebSocket |
| WebSocket + SSE in Go | `chatbot-go` | Go + Fiber + gorilla/websocket |
| Event-driven with Kafka | `marketplace-py` | FastAPI + Confluent Kafka |
| JWT auth + OAuth 2.0 | `auth-py` | FastAPI + PostgreSQL + Redis |
| NoSQL with MongoDB | `tax-py` | FastAPI + Motor (async MongoDB) |
| AI agent orchestration | `agentic-chat-py` | FastAPI + LangGraph + MCP |
| Full-stack React frontend | `customer-portal` | React + Vite + Tailwind |

---

## Quick Start

**Prerequisites:** Docker Desktop installed and running.

```bash
# Clone the repo
git clone <repo-url>
cd fullstack_chatbot_llm

# Start all services
docker compose up --build

# Open the frontend
open http://localhost:5173
```

Login with `demo` / `demo123`.

> See [GETTING_STARTED.md](GETTING_STARTED.md) for step-by-step setup and troubleshooting.

---

## Project Structure

```
fullstack_chatbot_llm/
├── docker-compose.yml          # Orchestrates all services + databases
├── docs/                       # Per-service learning guides
├── shared-py/                  # Reusable Python library (auth, errors, middleware)
├── shared-go/                  # Reusable Go library (auth, errors, middleware)
├── frontends/
│   └── customer-portal/        # React + Vite + Tailwind frontend
└── backends/
    ├── auth-py/                # JWT auth + Google OAuth
    ├── scheduler-py/           # Calendar events (Python + Postgres)
    ├── tax-py/                 # Corporate tax tracking (MongoDB)
    ├── todo-go/                # Todo list (Go + Postgres)
    ├── finance-py/             # Financial calculators (stateless)
    ├── validator-py/           # SSE streaming demo
    ├── chatbot-py/             # Real-time chat in Python (WebSocket/SSE/REST)
    ├── chatbot-go/             # Real-time chat in Go (WebSocket/SSE/REST)
    ├── marketplace-py/         # Kafka event-driven orders + payments
    └── agentic-chat-py/        # Multi-agent AI with LangGraph + MCP
```

---

## Service Ports

### Application Services

| Service | Port | Stack |
|---------|------|-------|
| Frontend | 5173 | React + Vite |
| Auth | 8005 | FastAPI + PostgreSQL + Redis |
| Scheduler | 7001 | FastAPI + PostgreSQL |
| Tax | 8007 | FastAPI + MongoDB |
| Todo | 8080 | Go + Fiber + PostgreSQL |
| Finance | 8001 | FastAPI (stateless) |
| Validator | 8002 | FastAPI + SSE |
| Chatbot (Python) | 8003 | FastAPI + WebSocket/SSE |
| Chatbot (Go) | 8004 | Go + Fiber + WebSocket/SSE |
| Marketplace API | 8006 | FastAPI + Kafka producer |
| Agentic Chat | 8010 | FastAPI + LangGraph + MCP |

### Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| PostgreSQL 16 | 5100 | Databases for auth, scheduler, todo |
| MongoDB 7 | 27100 | Database for tax service |
| Redis 7 | 6100 | OAuth state + AI job queue |
| Confluent Kafka | 19100 | Event streaming (marketplace) |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3110 | Metrics dashboard (`admin`/`admin`) |

---

## How Authentication Works

Every backend validates JWTs issued by `auth-py`. The frontend stores the token in `localStorage` and sends it as `Authorization: Bearer <token>` on every request.

| Username | Password | Role |
|----------|----------|------|
| `demo` | `demo123` | user |
| `admin` | `admin123` | admin |
| `user` | `user123` | user |

Google OAuth (PKCE flow) is also available — see [docs/backend-auth.md](docs/backend-auth.md).

---

## Architecture Overview

```
         ┌─────────────────────────────┐
         │  React + Vite (port 5173)   │
         └──────────┬──────────────────┘
                    │
         ┌──────────▼──────────────────────────────────────────┐
         │   Backend Services (all share JWT from auth-py)      │
         │  scheduler · todo · finance · validator · chatbot    │
         │  marketplace · tax · auth · agentic-chat             │
         └──────┬──────────┬──────────┬──────────┬─────────────┘
                ▼          ▼          ▼          ▼
          PostgreSQL    MongoDB     Redis    Confluent Kafka
```

The frontend uses a **Vite proxy** for REST services (`/scheduler-api`, `/todo-api`, etc.) and **direct connections** for WebSocket/SSE services.

---

## Learning Paths

**New to APIs?** Start with: `finance-py` (simplest) → `scheduler-py` (with a database) → `auth-py` (authentication)

**Want to learn real-time?** Start with: [docs/sse_usage.md](docs/sse_usage.md) → `validator-py` → [docs/websocket_usage.md](docs/websocket_usage.md) → `chatbot-py`

**Want to compare Python vs Go?** Look at: `chatbot-py` vs `chatbot-go` — same feature, two languages

**Want event-driven architecture?** Read: [docs/kafka_usage.md](docs/kafka_usage.md) → `marketplace-py`

**Want AI/LLM integration?** Read: [docs/backend-agentic-chat.md](docs/backend-agentic-chat.md) → `agentic-chat-py`

---

## Documentation

All per-service guides and technology deep-dives live in [`docs/`](docs/README.md).

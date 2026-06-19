# Documentation Index

Each document covers a specific service or technology. Start with whatever matches what you're trying to learn.

---

## Learn by Goal

### I want to learn REST APIs and databases
1. [Finance Backend](./backend-finance.md) — Simplest service, no database, pure computation
2. [Scheduler Backend](./backend-scheduler.md) — FastAPI + PostgreSQL + Alembic migrations (Python)
3. [Todo Backend](./backend-todo.md) — Go + Fiber + PostgreSQL (same concept, different language)
4. [Tax Backend](./backend-tax.md) — FastAPI + MongoDB (NoSQL instead of SQL)

### I want to learn authentication
1. [Auth Backend](./backend-auth.md) — JWT tokens, password hashing, Google OAuth 2.0, PostgreSQL + Redis

### I want to learn real-time communication
1. [SSE Deep-Dive](./sse_usage.md) — How Server-Sent Events work (one-way server streaming)
2. [Validator Backend](./backend-validator.md) — Simple SSE streaming example
3. [WebSocket Deep-Dive](./websocket_usage.md) — How WebSocket works (two-way real-time)
4. [Chatbot (Python)](./backend-chatbot-python.md) — WebSocket + SSE + REST in one service
5. [Chatbot (Go)](./backend-chatbot-go.md) — Same service built in Go (great for comparison)

### I want to learn event-driven architecture
1. [Kafka Deep-Dive](./kafka_usage.md) — How Kafka producers, consumers, and topics work
2. [Marketplace Backend](./backend-marketplace.md) — Full Kafka demo with order → payment flow

### I want to learn AI / LLM integration
1. [Agentic Chat Backend](./backend-agentic-chat.md) — Multi-agent orchestration with LangGraph + MCP tools

### I want to understand the frontend
1. [Frontend Auth](./frontend-auth.md) — Login, JWT storage, protected routes in React
2. [Frontend Chat](./frontend-chat.md) — WebSocket/SSE/REST protocols from the frontend
3. [Frontend Marketplace](./frontend-marketplace.md) — React UI for the Kafka demo

---

## All Service Docs

| Document | Service | Port | What it teaches |
|----------|---------|------|-----------------|
| [backend-auth.md](./backend-auth.md) | Auth | 8005 | JWT, OAuth 2.0, bcrypt, Redis |
| [backend-scheduler.md](./backend-scheduler.md) | Scheduler | 7001 | FastAPI CRUD, PostgreSQL, Alembic |
| [backend-tax.md](./backend-tax.md) | Tax | 8007 | MongoDB, Motor async driver |
| [backend-todo.md](./backend-todo.md) | Todo | 8080 | Go CRUD, pgx, golang-migrate |
| [backend-finance.md](./backend-finance.md) | Finance | 8001 | Stateless APIs, Pydantic validation |
| [backend-validator.md](./backend-validator.md) | Validator | 8002 | SSE streaming, async generators |
| [backend-chatbot-python.md](./backend-chatbot-python.md) | Chatbot (Python) | 8003 | WebSocket, SSE, REST polling |
| [backend-chatbot-go.md](./backend-chatbot-go.md) | Chatbot (Go) | 8004 | WebSocket, SSE in Go/Fiber |
| [backend-marketplace.md](./backend-marketplace.md) | Marketplace | 8006 | Kafka producer/consumer, AsyncAPI |
| [backend-agentic-chat.md](./backend-agentic-chat.md) | Agentic Chat | 8010 | LangGraph, MCP tools, Redis job queue |

## Technology Deep-Dives

| Document | Topic |
|----------|-------|
| [kafka_usage.md](./kafka_usage.md) | Kafka producers, consumers, topics, consumer groups |
| [websocket_usage.md](./websocket_usage.md) | WebSocket protocol, message format, connection lifecycle |
| [sse_usage.md](./sse_usage.md) | SSE protocol, async generators, EventSource vs fetch |

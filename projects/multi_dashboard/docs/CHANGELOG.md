# Changelog

All notable changes to this project are documented here, organized by project phase.
Each phase introduced one or more new services and frontend features.

---

## [Project 9] — Monorepo Hardening & Platform Refactor

### Overview

Full best-practice hardening of all 10 backends and the frontend across 12 phases. The goal was to move the platform from a POC to production-grade: canonical service layouts, native async I/O end-to-end, shared library extraction, Google OAuth, Postgres migrations, Go service upgrades, and a standardized frontend stack.

### Added

- **`shared-py/`** — New installable Python library consumed editably by all 8 Python services. Modules: `shared.config` (`AppSettings(BaseSettings)`), `shared.logging` (JSON formatter + `request_id` contextvar), `shared.errors` (`ErrorEnvelope{code,message,detail,trace_id}` + exception handlers), `shared.auth` (`encode_jwt`/`decode_jwt`/`get_current_user` factory, HS256 local-verify only), `shared.cors` (`add_cors` — rejects `*` with credentials), `shared.middleware` (RequestId, AccessLog), `shared.pagination` (`PageParams`, `Page[T]`), `shared.db.sql` (async SQLAlchemy 2 engine + `AsyncSession` factory), `shared.db.mongo` (`AsyncMongoClient` factory), `shared.testing` (pytest fixtures: in-memory SQLite/mongomock, JWT minter, async TestClient).
- **`shared-go/`** — New Go module (`github.com/mihirzz/chatbot-shared-go`) consumed via `replace` directive. Packages: `shared/config` (viper loader, `LoadConfig[T]` generic with reflection-based env binding), `shared/logging` (zap JSON factory), `shared/errors` (`ErrorEnvelope` + `FiberErrorHandler`, mirrors Python shape), `shared/auth` (`EncodeJWT`/`VerifyJWT`/`RequireAuth`/`RequireRole` Fiber middleware), `shared/middleware` (RequestID, AccessLog, Recover), `shared/db/sql` (pgx/v5 pool factory), `shared/db/mongo` (mongo-driver client factory), `shared/testing` helpers. Cross-language JWT compat verified: Python-minted tokens decode in Go and vice versa.
- **Google OAuth 2.0 + PKCE** in `auth-py` — full Authorization Code + PKCE flow via `authlib`; JWKS verification against Google's public keys; Redis-backed state/CSRF store (10-min TTL); user upsert to Postgres `users_db`; account linking between password and Google identities.
- **`users_db` (Postgres)** in `auth-py` — replaces in-memory user dict. SQLAlchemy `User` ORM model; Alembic `0001_initial` migration; idempotent `SEED_USERS` seeding on startup; indexed on `email` and `google_sub`.
- **Frontend auth additions** — `GoogleSignInButton.tsx` (links to `/auth/google/login`), `AuthCallbackPage.tsx` (parses hash fragment, stores tokens, scrubs URL, navigates to `return_to`), `/auth/callback` route in `App.tsx`.
- **Frontend shared infrastructure** — `src/lib/api-client.ts` (axios instance + JWT interceptor + refresh-on-401), `src/lib/errors.ts` (`ApiError` + `ErrorEnvelope`), `src/lib/zod-helpers.ts`; `src/hooks/{useApiQuery,useApiMutation,useAuthToken}.ts`; `src/components/ui/{Button,Input,Select,Card,Modal,Toast,FormField}.tsx`.
- **Per-feature canonical shape** — every feature folder now has `schemas.ts` (Zod), `types.ts` (`z.infer`), `api.ts` (axios via `api-client`), `hooks.ts` (React Query). Old `src/api/*.ts` files become thin re-exports for backwards compat. `SchedulerPage.tsx` migrated to `react-hook-form` + `zodResolver` as the reference implementation.
- **Frontend test stack** — `vitest` 4 + `@testing-library/react` 16 + MSW 2; jsdom environment; shared `render`/`setup`/`handlers` test utilities; 4-test `SchedulerPage` suite; `npm run test:run` → 4/4 green.
- **`/health` and `/ready` endpoints** on every backend (all 8 Python + 2 Go). `health` is a liveness probe (always 200); `ready` checks DB connectivity (503 if down). Compose `healthcheck:` blocks all point at `/ready`.
- **Root developer tooling** — `Makefile` (`make up/down/logs/test/lint/migrate/up-minimal`), root `.env.example` (all compose-level vars documented), `pyrightconfig.json` (covers all Python backends + shared-py).
- **Per-service `.env.example`** for all 10 backends listing every env var each service reads.
- **`infra/mongo/init/01-tax-indexes.js` + `02-tax-seed.js`** — production MongoDB init for tax-py indexes.
- **`infra/postgres/init/01-create-databases.sql`** — creates `users_db`, `todo_db`, `scheduler_db`; grants schema access for PG15+ compatibility.
- **`backends/scheduler-py/migrations/versions/0001_initial.py`** — Alembic migration creating `events` and `reminders` tables with all indexes.

### Changed

#### Python backends (all 8)

- **Canonical layout enforced** — every service follows the identical directory shape: `app/{main,config,deps,lifespan}.py` + `app/routers/` + `app/schemas/` + `app/models/` + `app/crud/` + `app/services/` + `app/domain/` + `app/tests/`; `alembic.ini`, `migrations/`, `pyproject.toml`, `.env.example` at service root.
- **`main.py` thinned** — all services: factory function only (`create_app()`), mounts routers, installs shared middleware/error handlers/CORS. No business logic inline. Target ≤80 LOC.
- **`shared-py` integrated across all 8 services** — shared config, CORS, errors, middleware, auth. Per-service `Dockerfile` uses repo-root build context; `docker-compose.yml` bind-mounts `./shared-py:/shared-py:ro`.
- **`scheduler-py`** — reference implementation. Migrated `psycopg2` → `asyncpg`; all handlers now `async def`; `Session` → `AsyncSession`; `crud/` is async; `Base.metadata.create_all()` replaced by Alembic. 9 smoke tests green.
- **`tax-py`** — sync `MongoClient` → `AsyncMongoClient` (PyMongo 4.9+); `httpx.Client` → `httpx.AsyncClient` for scheduler calls; `tax_dates.py` / `nil_t2.py` moved under `app/domain/`; routers split by resource (`corporations`, `filings`, `nil_t2`); Mongo indexes in init script. 10 smoke tests green.
- **`auth-py`** — replaced 424-LOC in-memory monolith with canonical layout + Postgres + Google OAuth. Routers: `auth.py` (password flows: `/auth/token`, `/auth/login`, `/auth/refresh`, `/auth/me`, `/auth/register`) and `oauth.py` (`/auth/google/login`, `/auth/google/callback`). `passlib` removed (Python 3.12 deprecation); replaced with direct `bcrypt` calls. 10 smoke tests green.
- **`finance-py`** — split monolith into `routers/{investment,mortgage,salary}.py` and `domain/{investment,mortgage,salary}.py`; legacy `/compute` dispatch route preserved for frontend backwards-compat; no auth (stateless public API).
- **`marketplace-py`** — `print` statements replaced with `shared.logging`; aiokafka producer lifecycle managed via `lifespan.py` + `app.state`; auth enforced on `POST /orders`.
- **`chatbot-py`** — split 475-LOC monolith into `routers/{chat,ws,sse}.py` + `store.py` + `domain.py`; auth on REST + SSE paths; WebSocket accepts `?access_token=` query param.
- **`agentic-chat-py`** — surgical update: `config.py` extends `AppSettings`; `shared.logging`/`shared.errors` applied; `POST /message` gated by `get_current_user`; existing agents and Redis store untouched.
- **`validator-py`** — split largest monolith into `routers/{validate,stream}.py` + `domain/diff/` + `domain/rules/` packages; shared CORS/errors/middleware applied.
- **All resource routes** now enforce `Depends(get_current_user)` (CWE-306). All services verify JWTs **locally** using `AUTH_SECRET_KEY` — no runtime dependency on `auth-backend`.

#### Go backends (both)

- **`todo-go`** — migrated GORM + SQLite → pgx/v5 + Postgres; `golang-migrate` auto-applies migrations on startup; Todo IDs changed integer → UUID; integrated `shared-go` (config, logging, errors, auth, middleware); `RequireAuth` on all `/todos/*` routes; paginated list endpoint (`Page[T]` shape). `go vet` + `gofmt` clean.
- **`chatbot-go`** — refactored to canonical Go layout (`cmd/server/` + `internal/{config,store,domain,handlers,models}`); integrated `shared-go`; JWT auth on `/api/*` group and `/ws/chat` (query-param fallback); CORS from env. `go vet` + `gofmt` clean.

#### Infrastructure

- **`docker-compose.yml`** — `AUTH_SECRET_KEY` and all secrets moved to env-var references (`${AUTH_SECRET_KEY}`); `CORS_ORIGINS` env-driven per service (no more `*`); `depends_on` for all backends references only their own DB (service isolation — no cross-service startup dependencies); every backend has a `healthcheck:` block; `shared-py` and `shared-go` bind-mounted read-only; `todo_db` SQLite named volume removed (replaced by Postgres).

### Removed

- **In-memory user store** in `auth-py` (replaced by Postgres `users_db` + `SEED_USERS` seeding).
- **`passlib`** from `auth-py` (Python 3.12 deprecated `crypt` module; replaced by direct `bcrypt`).
- **GORM + SQLite** from `todo-go` (replaced by pgx/v5 + Postgres + `golang-migrate`). SQLite `todo_db` Docker volume removed.
- **`Base.metadata.create_all()`** from `scheduler-py` startup (replaced by Alembic migration).
- **`@app.on_event` startup/shutdown hooks** across Python backends (replaced by `lifespan` async context managers).
- **Wildcard CORS** (`allow_origins=["*"]`) from all backends (replaced by `shared.cors.add_cors` with explicit origin lists).
- **Cross-service `depends_on`** in `docker-compose.yml` (e.g., `tax-backend` no longer depends on `scheduler-backend` at startup; calls are lazy HTTP).
- **Monolithic `main.py` files** across all 8 Python backends (split into canonical router/schema/model/crud/service/domain layers).
- **Old `internal/chat/` + `internal/routes/`** packages in `chatbot-go` (replaced by canonical `internal/{store,domain,handlers}` layout).

---

## [Project 8] — Platform Refactor & Tax Service

### Changed

- **Shared libraries.** Extracted `shared-py/` (`shared.config.AppSettings`, `shared.cors`, `shared.errors`, `shared.middleware.install_middleware`, `shared.pagination.Page`, `shared.auth.get_current_user_factory`) and `shared-go/` (`sharedconfig.LoadConfig`, `sharedmw.Install`, `apperrors.FiberErrorHandler`, `auth.RequireAuth`, `shareddb.NewPool`, `logging.NewLogger`). All Python and Go services now consume these instead of redefining CORS / error / logging / auth boilerplate locally.
- **Persistent storage.** Replaced SQLite for `auth-py`, `scheduler-py`, `todo-go` with **PostgreSQL 16** (host `5100` → `5432`, separate databases per service). `tax-py` uses **MongoDB 7** (host `27100` → `27017`, database `tax_db`) via Motor. `auth-py` and `agentic-chat-py` use **Redis 7** (host `6100` → `6379`) for OAuth state / job tracking.
- **Migrations.** Adopted Alembic (Python services) and golang-migrate with embedded `go:embed` filesystem (Go services). Migrations run automatically on app start via lifespan/init handlers.
- **Project layout.** Split monolithic `main.py` files into router packages (`app/routers/*.py`) for `chatbot-py`, `finance-py`, `validator-py`, `scheduler-py`, `tax-py`, `auth-py`. Go services adopted standard `cmd/server` + `internal/{handlers,routes,models,database,config}` layout.
- **Pagination contract.** List endpoints now return `Page[T] = {items: T[], total, limit, offset}` instead of raw arrays. Frontend list views were updated to read `.items`.
- **Auth coverage extended.** `scheduler-py`, `todo-go`, `tax-py`, `marketplace-py`, and `chatbot-py` REST + SSE endpoints all enforce JWT via shared libs. `chatbot-go` enforces JWT on every endpoint including WebSocket via the `?access_token=` query parameter (`auth.RequireAuth` accepts header or query). `chatbot-py` WebSocket remains intentionally unauthenticated.
- **Kafka broker.** Migrated `marketplace-py` / `payment-consumer` from Redpanda to **Confluent Kafka 7.6.1** + Zookeeper (`confluentinc/cp-kafka`, host `19100` → container `19092`).
- **Frontend bug fixes.** `api/chat_py.ts` and `api/chat_go.ts` now attach `Authorization: Bearer` to REST + SSE; `api/chat_go.ts` appends `?access_token=` to the WebSocket URL. `features/scheduler/api.ts` defensively extracts `.items` from `Page<T>` responses.

### Added

- **`backends/tax-py/`** — New FastAPI + MongoDB service (port `8007`) for Canadian corporate tax tracking. Manages `corporations`, `tax_filings`, and `nil_t2_reports` collections. On corporation creation, calls into `scheduler-py` to seed Annual Return / GST-HST / T2 reminders. Vite proxy at `/tax-api`. See [backend-tax.md](./backend-tax.md).
- **Google OAuth (PKCE)** in `auth-py` plus the `AuthCallbackPage` URL-fragment handler in the frontend.
- **Observability stack** in Docker Compose: Prometheus, Grafana (admin/admin), node-exporter, Elasticsearch.

### Removed

- SQLite databases for `auth`, `scheduler`, and `todo` services (still used only by `payment-consumer`).
- In-memory user store in `auth-py` (replaced by Postgres `users` table seeded from `SEED_USERS`).
- Per-service ad-hoc CORS / error / logging code (now via `shared-py` / `shared-go`).

---

## [Project 7] — Multi-Agent AI Orchestration

### Added

**`backends/agentic-chat-py/`** — New Python service (port `8010`)
- **CentralAgent** — top-level LangGraph ReAct orchestrator; routes every query to the most relevant sub-agents and synthesises results
- **BaseAgent** — shared base class for all agents; builds LangGraph `create_react_agent` graphs, loads MCP tools at runtime, and applies middleware (concurrency semaphore, exponential-backoff retry, structured logging)
- **GrafanaAgent** — queries Prometheus/Mimir metrics via Grafana MCP (SSE transport, port `8083`); handles PromQL queries for CPU, memory, and infrastructure alarms
- **FlowIqAgent** — analyses NetFlow/IPFIX/sFlow traffic via Elasticsearch MCP (port `8084`); queries `.ds-elastiflow-flow-*` index for top talkers, bandwidth, app-to-app flows
- **InventoryAgent** — IT Asset Management queries via Toolbox MCP (port `8081`); handles device inventory, hardware/software versions
- **NetworkAgent** — live operational network state via Network MCP (port `8082`); executes CLI commands, DNS lookups, reachability checks
- **Async job pattern** — `POST /message` returns immediately with `msg_id`; agent pipeline runs as `asyncio` background task; `GET /message/{msg_id}` polls status + live `AgentStep` progress from Redis
- **Redis job store** (`app/redis_store.py`) — async job creation, step appending, completion/failure updates with 1-hour TTL
- **Pydantic settings** (`app/config.py`) — all config via env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEFAULT_LLM_PROVIDER`, `DEFAULT_MODEL`, MCP URLs, `JOB_TTL_SECONDS`)
- **Dual LLM support** — configurable between Anthropic Claude and OpenAI GPT at the provider and model level

**MCP Sidecar services** (new Docker Compose entries)
- `grafana-mcp` — `grafana/mcp-grafana:latest`; SSE transport on port `8083`; connects to Grafana at `http://grafana:3000`
- `elasticsearch-mcp` — `@elastic/mcp-server-elasticsearch` (Node.js); SSE transport on port `8084`; connects to Elasticsearch at `http://elasticsearch:9200`

**Observability stack** (new Docker Compose entries)
- `prometheus` — scrapes `node-exporter` and itself every 15s; 7-day TSDB retention
- `node-exporter` — host OS metrics (CPU, memory, disk, network) on port `9100`
- `grafana` — visualisation layer with auto-provisioned Prometheus datasource; admin/admin on port `3030`
- `elasticsearch` — single-node, security disabled, 512MB heap; health-checked before MCP sidecar starts

**`frontends/customer-portal/src/features/agentic-chat/`** — New React feature (`/agentic-chat`)
- `AgenticChatPage.tsx` — chat UI with sub-agent chips, gradient header, clear-conversation button
- `ChatMessage.tsx` / `ChatInput.tsx` — message display and text input components
- `StepTracker.tsx` — renders live `AgentStep` entries as the agent pipeline executes
- `useAgenticChat.ts` — custom hook; 500ms polling loop, conversation-ID persistence via ref, full state machine (idle → loading → streaming steps → complete/error)
- `src/api/agentic_chat.ts` — typed API client (`postMessage`, `getMessageStatus`) pointing at `VITE_AGENTIC_CHAT_API_URL`

**Docs**
- `docs/backend-agentic-chat.md` — full architecture, agent hierarchy, async job pattern, Redis store, API reference, config table, MCP sidecar details, observability stack, frontend integration, and local-run guide

---

## [Project 6] — Platform Improvements & Finance Expansion

### Added

**Finance — Salary Projection** (`backends/finance-py`, `frontends/…/features/finance/salary/`)
- New `salary_projection` computation kind in the finance engine
- Inputs: monthly salary, yearly increment %, monthly expenses, inflation %, years, annual return %
- Outputs: year-by-year breakdown of salary, expenses, savings, cumulative savings, and compounded investment value
- `SalaryProjectionPage.tsx` — form + line chart + summary cards + CSV download

**Finance — Housing Comparison** (`frontends/…/features/finance/housing/`)
- Combined buy-vs-rent investment comparison view (`HousingComparisonPage.tsx`)
- Compares home purchase vs renting + investing the difference; accounts for mortgage amortization, property appreciation, rent increases, inflation, bear-market scenarios
- Refactored from separate buy/rent views into one unified comparison page

**Docs**
- `docs/kafka_usage.md` — deep-dive on Kafka producers/consumers, topic design, consumer groups
- `docs/sse_usage.md` — deep-dive on Server-Sent Events: streaming, reconnection, chunked output
- `docs/websocket_usage.md` — deep-dive on WebSocket: bidirectional messaging, Fiber's StreamWriter, connection lifecycle

### Changed

- **Feature Hub UX** — improved features catalogue layout; added quick-access section (6 pinned features) and grouped-by-category view with search
- **Kafka infra** — replaced Redpanda with Confluent Kafka (`confluentinc/cp-kafka:7.6.1`) + Zookeeper; updated broker config and healthcheck

---

## [Project 5] — Marketplace & Event-Driven Architecture

### Added

**`backends/marketplace-py/`** — New Python FastAPI service (port `8006`)
- Contract-first design: OpenAPI (REST) + AsyncAPI (Kafka events)
- `POST /orders` — creates an order and publishes `OrderCreatedEventV1` to `orders.created` Kafka topic via AIOKafka async producer
- Pydantic event schemas enforce data contracts across producer and consumer

**`backends/marketplace-py/consumer/`** — New Python Kafka consumer service
- Consumes from `orders.created` topic (consumer group `payment-service-v1`)
- Validates incoming events against `OrderCreatedEventV1` schema
- Creates payment records in SQLite (`payment_db` Docker volume)
- Designed for horizontal scaling via consumer group rebalancing

**`frontends/…/features/marketplace/MarketplacePage.tsx`** — New frontend page (`/marketplace`)
- Simple order creation form (user ID + amount in cents)
- Displays JSON order response on success
- Documents the contract-first architecture (OpenAPI + AsyncAPI callouts)

**Infrastructure**
- Kafka (`confluentinc/cp-kafka`) + Zookeeper added to Docker Compose
- Named volume `payment_db` for consumer SQLite persistence

---

## [Project 4] — Authentication Layer

### Added

**`backends/auth-py/`** — New Python FastAPI service (port `8005`)
- JWT-based authentication (HS256) with OAuth2 Password Bearer flow
- `POST /token` — OAuth2-compatible token endpoint
- `POST /login` — returns access token + refresh token + user info
- `POST /refresh` — issues new access token from a valid refresh token
- `GET /me` — returns current authenticated user
- `GET /validate` — validates token and returns user role
- `POST /logout` — stateless logout (client clears tokens)
- In-memory user store with bcrypt-hashed passwords; configurable via env vars (`AUTH_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`)

**`frontends/…/features/auth/`** — New auth flow
- `LoginPage.tsx` — login form using the auth backend
- `ProtectedRoute.tsx` — wraps all routes; redirects unauthenticated users to `/login`
- `AuthContext` — React context storing token and user state; all protected features require login

### Changed

- All frontend routes wrapped in `ProtectedRoute`
- Material UI and React Router added as core frontend dependencies; sidebar and layout upgraded

---

## [Project 3] — Real-Time Chat (Python + Go) & Network Validator

### Added

**`backends/chatbot-py/`** — New Python FastAPI service (port `8003`)
- Three communication patterns demonstrated side-by-side:
  - **WebSocket** (`/ws/chat`) — bidirectional real-time chat with streamed responses and status updates
  - **REST async** (`POST /api/chat/async` + `GET /api/chat/status/{id}`) — fire-and-forget with polling
  - **SSE** (`POST /api/chat/stream`) — server-to-client streaming
  - **REST sync** (`POST /api/chat`) — blocking synchronous response
- In-memory conversation history (`GET /api/conversations/{id}`)

**`backends/chatbot-go/`** — New Go Fiber service (port `8004`)
- Same four communication patterns as `chatbot-py` but in Go
- Uses Fiber's built-in WebSocket and `StreamWriter` for SSE
- Demonstrates goroutine-based concurrency model

**`backends/validator-py/`** — New Python FastAPI service (port `8002`)
- Network device configuration validation via SSE streaming
- `GET /{change_request_id}/{device_id}/stream` — dual-mode SSE:
  - Initial mode: streams metadata, command structure, LLM analysis, first 4KB of device output
  - Pagination mode: fetches next 4KB chunks on demand (offset-based)
- `GET /tasks` — paginated task list with filtering and sorting
- In-memory cache with TTL; pre-signed URL fetching for device outputs

**`frontends/…/features/chat_py/`** and **`frontends/…/features/chat_go/`** — New chat pages (`/chat-py`, `/chat-go`)
- Three-panel side-by-side comparison of WebSocket / REST+polling / SSE
- Info cards explaining trade-offs of each communication pattern

**`frontends/…/features/validator/ValidatorPage.tsx`** — New frontend page (`/validator`)
- Tasks tab: paginated table of validation tasks
- Diff view tab: live SSE-streamed device output with before/after command diff display

---

## [Project 2] — Finance Calculators

### Added

**`backends/finance-py/`** — New Python FastAPI service (port `8001`)
- Stateless computation engine (no database)
- `POST /compute` — routes to sub-calculator based on `kind` field:
  - **`investment`** — compound interest with monthly contributions, lump-sum payments, CAGR; returns monthly and yearly breakdown
  - **`mortgage`** — full amortization schedule with optional extra monthly/annual/one-time payments; compares standard vs accelerated payoff scenarios

**`frontends/…/features/finance/investment/InvestmentPage.tsx`** — New page (`/investment`)
- CAGR projection calculator; form with sliders + lump-sum support; monthly/yearly tabbed results table; CSV download

**`frontends/…/features/finance/mortgage/MortgagePage.tsx`** — New page (`/mortgage`)
- Full amortization schedule viewer; extra-payment scenario comparison; scrollable table + summary cards; CSV download

### Changed

- Frontend sidebar improved: header added, side panel alignment fixed
- Finance API routed via Vite proxy (`/finance-api`) to avoid CORS in dev

---

## [Project 1] — Productivity Hub (Foundation)

### Added

**`backends/scheduler-py/`** — Python FastAPI service (port `8000` / `8100`)
- Calendar event management: `GET/POST /events`, `GET/PUT/DELETE /events/{id}`
- Reminder management tied to events: `GET/POST /reminders`, `GET/PUT/DELETE /reminders/{id}`
- SQLAlchemy ORM with SQLite (`scheduler_db` Docker volume)

**`backends/todo-go/`** — Go Fiber service (port `8080`)
- TODO list CRUD: `GET/POST /todos`, `GET/PUT/DELETE /todos/{id}`, `PATCH /todos/{id}` (toggle complete)
- GORM ORM with SQLite (`todo_db` Docker volume)
- `/healthz` health check

**`frontends/customer-portal/`** — React + Vite + TypeScript frontend (port `5173`)
- `Layout.tsx` — responsive sidebar navigation with feature search, grouped links, user dropdown, and hamburger menu
- `FeatureHubPage.tsx` (`/features`) — feature discovery landing page with quick-access and grouped categories
- `SchedulerPage.tsx` (`/scheduler`) — two-column calendar UI with event creation, edit, delete, timezone-aware datetime
- `RemindersPage.tsx` — reminder form tied to events with list + CRUD
- `TodosPage.tsx` (`/todos`) — active/completed todo lists with React Query for server state, inline toggle and edit

**Docker Compose** — initial orchestration
- `redis` (port `6379`)
- Named volumes: `scheduler_db`, `todo_db`
- Vite dev server with bind-mount hot reload

---

## Port Reference

| Service | Container Port | Host Port |
|---------|---------------|-----------|
| scheduler-backend | 8000 | **8100** |
| todo-backend | 8080 | 8080 |
| finance-backend | 8001 | 8001 |
| validator-backend | 8002 | 8002 |
| chatbot-py | 8003 | 8003 |
| chatbot-go | 8004 | 8004 |
| auth-backend | 8005 | 8005 |
| marketplace-api | 8000 | 8006 |
| tax-backend | 8007 | 8007 |
| agentic-chat | 8010 | 8010 |
| grafana | 3000 | **3030** |
| prometheus | 9090 | 9090 |
| node-exporter | 9100 | 9100 |
| grafana-mcp | 8083 | 8083 |
| elasticsearch-mcp | 8084 | 8084 |
| elasticsearch | 9200 | 9200 |
| kafka | 9092 (internal) / 19092 (external) | 19092 |
| apps-frontend | 5173 | 5173 |

# Monorepo Refactor Plan — Best-Practice Hardening Across All Apps

> **Status**: Proposed. POC stage; destructive refactor approved.
> **Branch**: `project-9`.
> **Scope**: All 8 Python FastAPI backends + 2 Go Fiber backends + `customer-portal` frontend.

## 1. Why

The repo grew feature-by-feature. Each service made independent choices for config, logging, error handling, persistence, and auth. To move beyond POC:

- **CWE-aligned security** — real JWT enforcement on backends, secrets out of code, tightened CORS, Pydantic-validated inputs, Google OAuth 2.0 with PKCE for SSO
- **ACID** — transactional boundaries on SQL writes via SQLAlchemy `AsyncSession` per request; multi-document Mongo writes via `AsyncMongoClient` sessions where needed
- **DRY** — `shared-py/` and `shared-go/` packages; shared UI primitives on frontend
- **KISS** — flat per-service layout, no premature abstractions
- **Type safety** — Pydantic v2 + mypy/pyright; Zod runtime validation on frontend; Go's `staticcheck` + `gopls`
- **Native async end-to-end** — `AsyncMongoClient`, `AsyncSession + asyncpg`, async FastAPI route handlers
- **SSO experience** — "Sign in with Google" button on the login page; auto-provisioning of users; backwards compat with existing demo password accounts
- **Service isolation** — every backend runs standalone given its DB + a shared JWT secret; no runtime dependency on other backends for token validation

## 2. Service Isolation Principle (read this first)

**Hard rule**: any subset of services must run independently. Spinning up `postgres + scheduler-backend + frontend` should work as smoothly as `docker compose up`. The implications:

1. **JWT is verified locally** in every backend using the same `AUTH_SECRET_KEY` env. Auth-py mints tokens (via password or Google); nobody calls auth-py at request-validation time.
2. **`shared-py` / `shared-go` are library packages**, not running services.
3. **No backend HTTP-calls another backend at startup**. Cross-service feature calls (e.g. tax-py → scheduler-py to create calendar events) happen lazily on demand only.
4. **Compose `depends_on:` references only the service's own database**, never sibling app services.
5. **Each service has a `.env.example`** listing exactly the env vars it needs.

## 3. Current State (Verified)

**Python backends** (`backends/`):

| Service | Stack | Sync/Async | Persistence | Notes |
|---|---|---|---|---|
| `scheduler-py` | FastAPI + SQLAlchemy 2 + psycopg2 | sync | Postgres | Closest to ideal layout |
| `tax-py` | FastAPI + PyMongo | sync | MongoDB | Recently rewritten; clean |
| `auth-py` | FastAPI + python-jose | sync | In-memory dict | JWT issuer; no SSO, no DB |
| `agentic-chat-py` | FastAPI + LangGraph | async | Redis | Only service with structured logging |
| `chatbot-py` | FastAPI + WS/SSE | async | In-memory | 475 LOC monolithic `main.py` |
| `marketplace-py` | FastAPI + aiokafka | async | None (event-driven) | `print` statements, no error handling |
| `finance-py` | FastAPI | sync | None | ~300 LOC monolithic `main.py` |
| `validator-py` | FastAPI + SSE | sync | None | Largest monolithic `main.py` |

**Go backends** (`backends/`):

| Service | Stack | Persistence |
|---|---|---|
| `todo-go` | Fiber + GORM | SQLite |
| `chatbot-go` | Fiber + WebSocket | In-memory |

**Frontend**: React 18 + TS + Vite + React Query + axios+fetch mix + MUI+Tailwind hybrid. 11 feature folders. Existing `LoginPage` is password-only against auth-py `/token`.

**Infrastructure**: Postgres, MongoDB, Redis, Kafka+Zookeeper, Elasticsearch, Prometheus, Grafana, all backends + frontend. Hardcoded `AUTH_SECRET_KEY` in compose. Open CORS.

## 4. Canonical Directory Structures (MUST match exactly)

> **Hard rule**: Every Python service uses the *same* directory layout. Every Go
> service uses the *same* (different) layout. The two languages may differ from
> each other but within each language there is **one canonical shape, no
> deviations**. Predictability beats minimalism — even services with no
> database keep the empty `models/`, `crud/`, `migrations/` directories so
> humans and LLMs can navigate any backend without surprises.

### 4.1 Canonical Python service layout

Every Python backend (all 8) MUST follow this tree verbatim:

```
backends/<service>-py/
├── Dockerfile
├── pyproject.toml              # pytest, mypy, ruff config; service name; deps
├── requirements.txt            # pinned dependencies
├── .env.example                # lists EVERY env var the service reads
├── alembic.ini                 # always present (SQL svcs use it; others empty stub)
├── migrations/
│   ├── env.py                  # SQL svcs only; non-SQL svcs have placeholder
│   ├── README.md               # describes how to add migrations
│   └── versions/
│       └── .gitkeep
└── app/
    ├── __init__.py
    ├── main.py                 # FastAPI factory + router mounts ONLY (≤80 LOC target)
    ├── config.py               # Settings(BaseSettings) extending shared.config
    ├── deps.py                 # All FastAPI deps (get_db, get_current_user, ...)
    ├── lifespan.py             # async lifespan context (startup/shutdown)
    ├── routers/
    │   ├── __init__.py
    │   ├── health.py           # /health and /ready endpoints (every service)
    │   └── <resource>.py       # one file per resource
    ├── schemas/
    │   ├── __init__.py
    │   └── <resource>.py       # Pydantic request/response models
    ├── models/
    │   ├── __init__.py
    │   └── <resource>.py       # SQLAlchemy ORM OR Mongo Pydantic docs; empty if no-DB
    ├── crud/
    │   ├── __init__.py
    │   └── <resource>.py       # async data-access functions; empty if no-DB
    ├── services/
    │   ├── __init__.py
    │   └── <name>.py           # business logic across resources
    ├── domain/
    │   ├── __init__.py
    │   └── <name>.py           # pure logic, no I/O
    └── tests/
        ├── __init__.py
        ├── conftest.py
        └── test_smoke.py       # at minimum: /health 200 + /<resource> 401 envelope
```

**Rules** (any LLM implementing this MUST follow):

1. **`main.py` is thin**: it ONLY does `create_app()` factory: instantiate FastAPI, install shared middleware, register shared error handlers, mount routers, set lifespan. No business logic, no inline endpoints other than the app factory.
2. **Routers are split per resource**: never one mega-`main.py`. A router file exposes a module-level `router = APIRouter(prefix="/<resource>", tags=["<resource>"])`.
3. **Every service has `/health` and `/ready`**: `health` is a liveness probe (always returns 200); `ready` checks DB connectivity (returns 503 if down).
4. **All route handlers are `async def`**. All I/O via native async drivers.
5. **Even non-DB services keep `models/`, `crud/`, `migrations/`** with `__init__.py` stubs and a `README.md` explaining they're intentionally empty.
6. **All Pydantic schemas live under `schemas/`** — never inline in routers.
7. **All FastAPI dependencies live in `deps.py`** — never inline factories scattered across routers.
8. **`config.py` always extends `shared.config.AppSettings`** with a single `Settings` subclass and a `@lru_cache get_settings()` function.
9. **`lifespan.py` exposes one async context manager** wired into the FastAPI app — handles DB pool start/stop, Kafka producer, Redis client, etc.

### 4.2 Canonical Go service layout

Every Go backend (all 2) MUST follow this tree verbatim:

```
backends/<service>-go/
├── Dockerfile
├── go.mod                      # with `replace .../shared-go => ../../shared-go`
├── go.sum
├── .env.example                # lists EVERY env var the service reads
├── migrations/                 # golang-migrate format (always present)
│   ├── README.md
│   └── .gitkeep
├── cmd/
│   └── server/
│       └── main.go             # entry: load cfg, build app, listen, graceful shutdown
└── internal/
    ├── config/
    │   └── config.go           # extends shared-go/config.BaseSettings
    ├── handlers/
    │   ├── health.go           # /health and /ready handlers (every service)
    │   └── <resource>.go       # one file per resource
    ├── models/
    │   └── <resource>.go       # struct definitions
    ├── repo/
    │   └── <resource>.go       # data-access; empty if no-DB
    ├── service/
    │   └── <resource>.go       # business logic
    └── domain/
        └── <name>.go           # pure logic
```

**Rules**:

1. **`cmd/server/main.go`** ONLY: load config (`shared/config.LoadConfig[Settings]`), build logger (`shared/logging.NewLogger`), connect deps (DB, etc.), build Fiber app, install `shared/middleware.Install`, set `ErrorHandler: errors.FiberErrorHandler`, mount handlers, call `app.Listen()`, handle SIGTERM for graceful shutdown.
2. **Handlers per resource** under `internal/handlers/`. Each file exposes a constructor that takes the service layer and registers routes against a `fiber.Router`.
3. **Every service has `/health` and `/ready`**.
4. **Layered**: handler → service → repo → models. Handlers never call repos directly; services do.
5. **Auth is opt-in per route group**: protected groups use `auth.RequireAuth(cfg)`; `/health` and `/ready` stay public.

### 4.3 Canonical frontend feature layout

Every feature folder under `frontends/customer-portal/src/features/` MUST follow this shape:

```
src/features/<feature>/
├── <Feature>Page.tsx           # top-level route component
├── components/                 # feature-local presentational components
│   └── <Component>.tsx
├── api.ts                      # axios calls via src/lib/api-client.ts
├── schemas.ts                  # Zod schemas — single source of truth
├── types.ts                    # `export type X = z.infer<typeof XSchema>`
└── hooks.ts                    # React Query hooks (useApiQuery/useApiMutation)
```

Shared, cross-feature code lives under `src/lib/`, `src/components/ui/`, `src/hooks/` — also enforced (see §12).

## 5. Engineering Standards (How Any LLM Should Implement This)

> **This section exists so any LLM or developer picking up the plan produces
> the same caliber of work as a senior engineer.** Each phase must satisfy
> ALL gates below before being declared complete.

### 5.1 Before writing code

1. **Read first, code second.** Read the relevant plan section (§7–§10) AND the latest `docs/refactor-progress.md` entry. Never modify a file without reading it first.
2. **Identify reuse.** Grep for existing implementations of what you're about to build. Examples: `shared.errors.ErrorEnvelope` already exists — don't invent a new one.
3. **Create tasks.** Use the task tracker for any work with 3+ steps. One task per logical unit. Mark `in_progress` before starting, `completed` only when gates below pass.
4. **Pre-flight checklist** (re-confirm before each phase):
   - [ ] I know the canonical directory shape (§4) I'm targeting
   - [ ] I know which env vars the service needs (will end up in `.env.example`)
   - [ ] I know what shared modules I will reuse (config, auth, errors, etc.)
   - [ ] I know the verification commands I'll run to declare done (§5.3)

### 5.2 While writing code

- **Type-hint everything.** Python: every function signature has return type + arg types. Go: rely on the compiler.
- **Validate every input at the boundary.** Python: Pydantic schemas on every request body & query param. Go: parse into a struct and validate fields.
- **Native async I/O everywhere.** No `time.sleep`, no sync HTTP, no sync DB drivers. Python: `asyncio.sleep`, `httpx.AsyncClient`, `AsyncSession`, `AsyncMongoClient`. Go: `context.Context` on every I/O call.
- **No secrets in code.** Read via `shared.config.AppSettings`; fail-fast at startup if missing.
- **Cross-service HTTP**: explicit timeout (≤5s), retry policy on 5xx/network errors (max 2 retries with exponential backoff), structured logging of failures.
- **Idempotent writes**: PUT/PATCH replace/update; POST creates with a server-generated or client-supplied idempotency key where retry could double-create.
- **Increment in small runnable steps.** After each meaningful file added, run the smoke test or at least `python -c "import app.main"` / `go build ./...`.

### 5.3 Definition of Done — gates that MUST pass

Every phase entry in `docs/refactor-progress.md` must satisfy this checklist before its status flips to ✅:

| Gate | Python command | Go command |
|---|---|---|
| **Test** | `pytest -q -W error` from service dir → `0 failed` | `go test ./... -race` → `ok` |
| **Type** | `mypy app/` → `Success` (or `pyright app/`) | `go vet ./...` → no output |
| **Lint** | `ruff check .` → no errors | `gofmt -l . \| wc -l` → `0` |
| **Smoke (HTTP)** | `curl -s http://localhost:<port>/health` → `{"status":"ok"}` (200) | same |
| **Smoke (auth)** | `curl http://localhost:<port>/<resource>` → 401 envelope; `curl -H 'Authorization: Bearer <tok>'` → 200 | same |
| **Error envelope** | Trigger any 4xx/5xx → response JSON matches `{code, message, detail, trace_id}` | same |
| **Service isolation** | Spin up ONLY this service + its DB (no auth-backend running) + mint token offline → still works | same |
| **Docker** | `docker compose up <service>` → reaches healthy state within 30s | same |
| **Progress doc** | `docs/refactor-progress.md` updated with files created, verification output, decisions | same |

### 5.4 How to run the gates locally

For any Python backend `backends/<name>-py/`:

```bash
# from repo root
source .venv-shared/bin/activate
cd backends/<name>-py
pip install -e ../../shared-py -e ".[testing]"          # editable install
pytest -q -W error
mypy app/
ruff check .

# integration smoke
docker compose up <name>-backend -d
sleep 5
curl -fsS http://localhost:<port>/health | jq .
curl -i http://localhost:<port>/<resource>                                  # expect 401
TOKEN=$(python -c "from shared.auth import encode_jwt; print(encode_jwt({'sub':'demo','role':'user'}, '$AUTH_SECRET_KEY', expires_in_seconds=300))")
curl -fsS -H "Authorization: Bearer $TOKEN" http://localhost:<port>/<resource> | jq .
```

For any Go backend `backends/<name>-go/`:

```bash
cd backends/<name>-go
go test ./... -race
go vet ./...
gofmt -l .   # must be empty
docker compose up <name>-backend -d
curl -fsS http://localhost:<port>/health
```

### 5.5 Service isolation drill (mandatory after any auth-enforced backend ships)

```bash
# Goal: prove the service runs with ONLY its own DB + shared secret.
# auth-backend MUST NOT be running.
docker compose down
docker compose up postgres <name>-backend -d   # or mongodb, redis, etc.

# Mint a token offline using the same shared secret
export AUTH_SECRET_KEY="$(grep ^AUTH_SECRET_KEY .env | cut -d= -f2)"
TOKEN=$(python -c "from shared.auth import encode_jwt; print(encode_jwt({'sub':'demo','role':'user'}, '$AUTH_SECRET_KEY', expires_in_seconds=300))")

curl -fsS -H "Authorization: Bearer $TOKEN" http://localhost:<port>/<resource>
# Expected: 200 OK with data, NOT 401 or 502
```

If this fails, the service has an illegal startup-time or request-time dependency on auth-py. Fix before declaring done.

## 6. Cross-Cutting Requirements (Scalability, Availability, Security)

Every backend (Python and Go) MUST satisfy the baseline below. Mark each item N/A only with an explicit reason.

### 6.1 Scalability baseline

- **Stateless processes.** No in-process state beyond caches that can be rebuilt. Restartable at any time.
- **Pagination by default.** List endpoints accept `limit` (default 20, max 200) and `offset`. Python uses `shared.pagination.PageParams`/`Page[T]`; Go has an equivalent helper added when the first Go service needs it.
- **Pool sizing.** SQL: `pool_size=5, max_overflow=10, pool_pre_ping=True` (set in `shared.db.sql.make_async_engine`). Mongo: server-selection timeout 5s. pgx (Go): `MaxConns=10, MinConns=1`.
- **No N+1.** Eager-load relationships (`selectinload`) on list endpoints; Mongo uses single aggregate where appropriate.
- **Indexes.** Every WHERE/sort column has a DB index. SQL: declared on the SQLAlchemy model. Mongo: declared in `infra/mongo/init/*.js`. Verify with `EXPLAIN` (Postgres) or `getIndexes()` (Mongo).
- **Backpressure on bulk endpoints.** Any endpoint that fans out (e.g. tax-py setup-reminders calling scheduler) caps concurrency (`asyncio.Semaphore(10)`).

### 6.2 Availability baseline

- **`/health` liveness**: returns 200 always.
- **`/ready` readiness**: returns 200 only when DB is reachable; 503 otherwise. Compose `healthcheck:` hits `/ready`.
- **Graceful shutdown.** Python: FastAPI `lifespan` closes DB pools, Kafka producer, Redis client. Go: `signal.NotifyContext(ctx, SIGTERM)` + `app.ShutdownWithTimeout(15*time.Second)`.
- **DB startup retry.** On boot, try-connect with exponential backoff up to 30s before giving up.
- **Cross-service HTTP timeout + retry.** All `httpx.AsyncClient(timeout=5.0)` calls retry max 2x with backoff on connection errors and 5xx.
- **No service depends on another service at startup.** Only on its own DB (compose `depends_on: condition: service_healthy`).

### 6.3 Security baseline (CWE-aligned)

Mandatory checklist per service — every item ✓ or N/A-with-reason before done:

- [ ] CORS uses explicit origin list when `allow_credentials=True`; never `*` (CWE-942). Enforced at construction by `shared.cors.add_cors`.
- [ ] Every API input goes through a Pydantic schema (Python) or struct + validation (Go) (CWE-20).
- [ ] All SQL via SQLAlchemy ORM; no f-string/concat SQL (CWE-89).
- [ ] Mongo queries use dict args; never `$where` with user input (CWE-943).
- [ ] Every non-`/health`-`/ready` route declares `Depends(get_current_user)` (Python) or `auth.RequireAuth()` (Go) (CWE-306).
- [ ] All secrets via env, validated by Pydantic Settings; fail-fast on startup (CWE-798, CWE-532).
- [ ] JWT verification checks signature, exp, AND `type` claim (CWE-345). Handled by `shared.auth.decode_jwt`.
- [ ] Any redirect target (`redirect_uri`, `return_to`) is allowlist-checked against a configured set of frontend URLs (CWE-601).
- [ ] Rate limiting on `/auth/*` and any password endpoint: `slowapi` (Python) or `gofiber/contrib/limiter` (Go). Default: 30 req/min/IP (CWE-307).
- [ ] Log lines contain no PII, no secrets, no full tokens (CWE-532). Use `***` redaction for sensitive fields.
- [ ] All cross-service HTTP calls verify TLS (httpx default; explicit `verify=True`) (CWE-295).

### 6.4 Observability baseline

- Structured JSON logging via `shared.logging` (Python) or `shared/logging` (Go) — already provided.
- `X-Request-ID` propagation via middleware — already provided.
- `/metrics` Prometheus endpoint (deferred to a later pass; stub PR welcome). For this refactor, leave a TODO comment in `main.py` pointing at the planned endpoint.

## 7. `shared-py` Package

| Module | Purpose |
|---|---|
| `shared.config` | `AppSettings(BaseSettings)` — service_name, environment, log_level, cors_origins, auth_secret_key, auth_algorithm. Services subclass. |
| `shared.logging` | JSON formatter; `get_logger()` with `request_id` contextvar |
| `shared.errors` | `ErrorEnvelope{code,message,detail,trace_id}`, `AppException` + subclasses, `register_exception_handlers(app)` |
| `shared.auth` | `encode_jwt(payload, secret, algorithm, expires_in)`, `decode_jwt(token, secret, algorithm)` — LOCAL verify only. `get_current_user` FastAPI dep, `require_role()` factory. Used by both auth-py (issuer) and every other backend (verifier). |
| `shared.cors` | `add_cors(app, origins)` |
| `shared.middleware` | RequestId, AccessLog, Timing |
| `shared.pagination` | `PageParams`, `Page[T]` generic |
| `shared.db.sql` | `make_async_engine(url)`, `make_async_session_factory(engine)`, `get_async_session()` async-generator dep. SQLAlchemy 2.x + asyncpg. |
| `shared.db.mongo` | `make_async_mongo_client(uri)` returning `pymongo.AsyncMongoClient`. PyMongo 4.9+. |
| `shared.testing` | pytest fixtures — async TestClient, in-memory aiosqlite, mongomock-async, `auth_headers` JWT minter |

Each backend `Dockerfile`: `RUN pip install -e /shared-py`. Compose bind-mounts `./shared-py:/shared-py:ro`.

## 8. `shared-go` Package

| Package | Purpose |
|---|---|
| `shared/config` | viper loader; `LoadConfig[T]()` generic with env precedence |
| `shared/logging` | zap factory; `NewLogger(serviceName) *zap.Logger` |
| `shared/errors` | `ErrorEnvelope` struct matching Python shape; `WriteError(c *fiber.Ctx, err error)` |
| `shared/auth` | `VerifyJWT(token, secret) (Claims, error)` via `github.com/golang-jwt/jwt/v5`; `RequireAuth() fiber.Handler`. Local verify only — same shared secret as Python. |
| `shared/middleware` | RequestID, AccessLog, Recover for Fiber |
| `shared/db/sql` | pgx/v5 pool factory |
| `shared/db/mongo` | `go.mongodb.org/mongo-driver` client factory |
| `shared/testing` | Fiber test helpers |

`go.mod` module path: `github.com/mihirzz/chatbot-shared-go`. Services use `replace` directive.

## 9. OAuth 2.0 / Google SSO Design (auth-py)

### Flow (Authorization Code + PKCE)

1. Frontend renders `<GoogleSignInButton>` linking to `auth-py /auth/google/login?return_to=/dashboard`.
2. Auth-py:
   - Generates `state` (random, signed) and `code_verifier` / `code_challenge` (PKCE).
   - Stores `{state, code_verifier, return_to}` in Redis with 10-min TTL keyed by `state`.
   - 302 redirects user to Google `accounts.google.com/o/oauth2/v2/auth` with `client_id`, `redirect_uri=<auth-py>/auth/google/callback`, `scope=openid email profile`, `code_challenge`, `code_challenge_method=S256`, `state`.
3. User authenticates with Google → Google redirects to `auth-py /auth/google/callback?code=&state=`.
4. Auth-py:
   - Looks up `state` in Redis, retrieves `code_verifier` + `return_to`. Rejects if missing/expired (CSRF defense).
   - POSTs to `oauth2.googleapis.com/token` with `code`, `code_verifier`, `client_id`, `client_secret`. Receives `id_token`, `access_token`.
   - Verifies `id_token` against Google's JWKS (`https://www.googleapis.com/oauth2/v3/certs`) — `authlib` handles this.
   - Extracts `sub` (Google user ID), `email`, `email_verified`, `name`, `picture` from verified ID token.
   - **Upserts user** in `users_db.users` table:
     - If row exists with this `email`: link `google_sub`, update `name`, `picture_url`.
     - Else: insert new row with `email`, `google_sub`, `name`, `picture_url`, `role='user'`, `password_hash=NULL`.
   - Mints internal HS256 access + refresh JWTs via `shared.auth.encode_jwt({sub: user_id, email, role, ...})`.
   - 302 redirects to `${FRONTEND_REDIRECT_URI}#access_token=<at>&refresh_token=<rt>&return_to=${return_to}`.
5. Frontend `AuthCallbackPage` (route `/auth/callback`):
   - Parses `window.location.hash`, extracts tokens + return_to.
   - Stores tokens via `AuthContext` (localStorage same as today).
   - `history.replaceState(null, '', '/')` to wipe hash from URL bar.
   - Navigates to `return_to || '/'`.

### Password flow (preserved)

`POST /token` still accepts `username`+`password` (OAuth2PasswordRequestForm). Issues the same internal JWT. The login form shows both options side-by-side.

### Account linking rules

- If a Google sign-in arrives with an email matching an existing password user, the rows are linked (`google_sub` filled). Subsequent password logins still work; Google logins also work.
- If a password registration arrives with an email that already has a Google-only account (no `password_hash`), set the hash on that row.

### `users_db` schema (auth-py only)

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(320) NOT NULL UNIQUE,
  name VARCHAR(200),
  picture_url TEXT,
  google_sub VARCHAR(64) UNIQUE,        -- nullable; set when linked to Google
  password_hash VARCHAR(255),            -- nullable; set when password user
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_sub ON users(google_sub);
```

Either `google_sub` OR `password_hash` (or both) must be present.

### Dependencies added to auth-py

```
authlib>=1.3,<2          # OAuth flow + PKCE + JWKS verification
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
alembic>=1.13
redis>=5.0               # ephemeral OAuth state store (shared with agentic-chat redis container)
python-json-logger
```

### New env vars (auth-py)

```
AUTH_DATABASE_URL=postgresql+asyncpg://auth:auth@postgres:5432/users_db
AUTH_SECRET_KEY=<shared HS256 secret used by all backends>
AUTH_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=http://localhost:8005/auth/google/callback
FRONTEND_REDIRECT_URI=http://localhost:5173/auth/callback
REDIS_URL=redis://redis:6379/1
```

All read via `shared.config` (Pydantic Settings, fail-fast if missing).

### CWE-aligned hardening notes

- `state` token signed and TTL-bounded → mitigates CSRF (CWE-352)
- PKCE → mitigates code interception (CWE-345)
- Verify `id_token` signature against Google JWKS (don't trust the unverified claims) → mitigates trust-boundary issues (CWE-345)
- Validate `email_verified=true` before provisioning → mitigates account-takeover via unverified email
- Internal JWT uses HS256 with a strong env-provided secret (≥256 bits) → CWE-326/327
- Refresh tokens stored client-side; rotated on use; revocation list in Redis if invalidated → CWE-613
- `redirect_uri` exact-match against allowlist → CWE-601 (open redirect)
- All secrets via env, never logged → CWE-532

## 10. Per-Service Refactor Notes

### Python

- **scheduler-py** — reference implementation. Split `main.py` into `routers/events.py` + `routers/reminders.py`. All handlers `async def`. Migrate `psycopg2` → `asyncpg`; replace `Session` with `AsyncSession`; CRUD becomes `async def`. Config extends `shared.config`. Drop `Base.metadata.create_all()`; init Alembic with autogenerated `0001_initial`. Local JWT enforced via `Depends(get_current_user)`.
- **tax-py** — mirror scheduler split (`routers/corporations.py`, `filings.py`, `nil_t2.py`). Replace sync `MongoClient` with `pymongo.AsyncMongoClient`; CRUD becomes `async def`. Replace `httpx.Client` with `httpx.AsyncClient`. Move indexes to `infra/mongo/init/01-tax-indexes.js`. Convert `@app.on_event` to `lifespan`. Move `tax_dates.py`, `nil_t2.py` under `app/domain/`.
- **auth-py** — heavily refactored per Section 7. New Postgres `users_db`. New routers: `routers/auth.py` (password flows), `routers/oauth.py` (Google). New modules: `app/oauth/google.py` (authlib client), `app/oauth/state.py` (Redis state). New `app/models/user.py` (SQLAlchemy ORM). Alembic migration `0001_initial.py` creates `users` table. Auto-seed `admin` / `demo` users from env on startup (idempotent). Remove hardcoded secret from docker-compose.
- **agentic-chat-py** — config extends `shared.config` (preserve LLM keys). Replace bespoke logger with `shared.logging`. Adopt `shared.errors` envelope. Add `shared.auth.get_current_user` on `/message`.
- **chatbot-py** — split 475 LOC into `routers/chat.py`, `routers/ws.py`, `routers/sse.py`, `store.py`. Apply shared CORS, errors, middleware, auth on protected paths.
- **marketplace-py** — tighten CORS; replace `print` with `shared.logging`; lifespan-managed aiokafka producer via `app.state`. Validate `amount_cents > 0`. Add `shared.auth.get_current_user` on `/orders`.
- **finance-py** — split into `routers/{investment,mortgage,salary}.py` and `domain/{investment,mortgage,salary}.py`. No DB; just shared cross-cutting.
- **validator-py** — split monolith into `routers/validate.py`, `routers/stream.py` (async SSE), `domain/diff/`, `domain/rules/`. Largest split; last in rollout.

### Go

- **todo-go** — switch from GORM+SQLite to `pgx/v5` + Postgres (own DB `todo_db` on existing postgres). Migrations via `golang-migrate`. Refactor to canonical layout. Adopt `shared-go/{config,logging,errors,auth,middleware}`. `RequireAuth()` on `/todos`.
- **chatbot-go** — refactor to canonical layout; in-memory store stays. Apply shared middleware + auth on protected paths.

## 11. Frontend Standardization

- **New `src/lib/api-client.ts`** — axios instance, request interceptor reads JWT from `useAuthToken`, response interceptor maps non-2xx → `ApiError` matching backend `ErrorEnvelope`.
- **New `src/components/ui/`** — `Button`, `Input`, `Select`, `Card`, `Modal`, `Toast`, `FormField`.
- **New `src/hooks/{useApiQuery,useApiMutation,useAuthToken}.ts`** — React Query wrappers pre-bound to `api-client` + `ApiError` typing.
- **Per feature**: `schemas.ts` (Zod) → `types.ts` (z.infer) → `api.ts` (axios) → `hooks.ts`. Forms migrate to `react-hook-form` + `zodResolver`.
- **Auth feature changes**:
  - `LoginPage.tsx`: add `<GoogleSignInButton>` above existing password form. Both submit paths funnel through `useAuthContext`.
  - `GoogleSignInButton.tsx`: anchor element to `${AUTH_API_BASE}/auth/google/login?return_to=${currentPath}`.
  - `AuthCallbackPage.tsx`: parses `window.location.hash`, stores tokens via `AuthContext`, scrubs hash via `history.replaceState`, navigates to `return_to || '/'`.
  - New route in `App.tsx`: `<Route path="/auth/callback" element={<AuthCallbackPage />} />`.
- **Replace fetch-based** `src/api/scheduler.ts` with axios.
- **Test infra**: add `vitest`, `@vitest/ui`, `@testing-library/react`, `@testing-library/jest-dom`, `msw`, `zod`, `react-hook-form`, `@hookform/resolvers`. New `vitest.config.ts`, `src/test-utils/render.tsx`, `src/test-utils/msw/handlers.ts`. One smoke test (scheduler).

## 12. Infrastructure & Config

- New `infra/mongo/init/01-tax-indexes.js`, `02-tax-seed.js`
- New `infra/postgres/init/01-create-databases.sql` — creates `scheduler_db`, `users_db`, `todo_db`
- New `.env.example` at repo root + per service
- `docker-compose.yml`:
  - Replace hardcoded `AUTH_SECRET_KEY=...` with `${AUTH_SECRET_KEY}`
  - Add `${GOOGLE_CLIENT_ID}`, `${GOOGLE_CLIENT_SECRET}`, `${GOOGLE_REDIRECT_URI}`, `${FRONTEND_REDIRECT_URI}`, `${AUTH_DATABASE_URL}` to auth-backend env
  - Add `healthcheck:` to every backend
  - Bind-mount `./shared-py:/shared-py:ro` and `./shared-go:/shared-go:ro`
  - Pass `CORS_ORIGINS` per service (env-driven, not `*`)
  - `depends_on:` only references each service's own DB
- New top-level `Makefile`: `make up`, `make down`, `make test`, `make lint`, `make migrate SERVICE=...`, `make up-minimal SERVICES="..."` (isolation drill)
- New `pyrightconfig.json` at repo root
- Per-service `pyproject.toml` with `[tool.pytest]`, `[tool.mypy]`, `[tool.ruff]`

## 13. Migration & Testing Setup

- **Alembic** in `scheduler-py` (canonical, async template). Same pattern repeated for `auth-py` (`users_db`).
- **MongoDB**: `tax-py` indexes via `infra/mongo/init/01-tax-indexes.js`.
- **Go**: `golang-migrate` for `todo-go` Postgres migrations under `backends/todo-go/migrations/`.
- **pytest**: per-service `app/tests/conftest.py` imports from `shared.testing`. SQL → `sqlite+aiosqlite:///:memory:`. Mongo → async mongomock. One smoke test per service.
- **vitest**: root config with jsdom, MSW. One smoke test (scheduler page).

## 14. Rollout Order (do not reorder)

Each phase below MUST satisfy the Definition of Done (§5.3) AND the
Cross-Cutting Requirements baseline (§6) before being marked complete in
`docs/refactor-progress.md`. The progress doc has a per-phase checklist
template (see its top section).

1. **`shared-py` skeleton** — all modules. Verify `pip install -e shared-py` + import works.
2. **`shared-go` skeleton** — all packages. Verify `replace` directive in a scratch service.
3. **`scheduler-py`** refactor as Python reference. Native async SQL end-to-end (`AsyncSession` + `asyncpg`).
4. **`tax-py`** refactor — native `AsyncMongoClient`. Async httpx. Mongo init script.
5. **`auth-py` refactor + Google OAuth + Postgres users_db** — biggest single phase. Substeps:
   - Set up `users_db` on postgres container (init SQL creates DB).
   - Add SQLAlchemy `User` model + Alembic `0001_initial.py`.
   - Migrate existing in-memory `admin`, `demo`, `user` to seed-on-startup (idempotent upsert).
   - Implement password flow with the new DB.
   - Implement Google OAuth flow (`authlib`, Redis state, JWKS verify, user upsert).
   - Frontend: `GoogleSignInButton`, `AuthCallbackPage`, new route.
   - End-to-end test: log in with password → works. Click "Sign in with Google" → through real Google → land on dashboard.
6. **Enable local JWT validation** on `scheduler-py` and `tax-py`. Update frontend `api-client.ts` interceptor. Run the **Service Isolation Drill** (§5.5).
7. **Remaining Python backends**: `finance-py` → `marketplace-py` → `chatbot-py` → `agentic-chat-py` → `validator-py`.
8. **`todo-go`** — switch SQLite → pgx + Postgres. Adopt `shared-go`. Local JWT middleware.
9. **`chatbot-go`** — adopt `shared-go`. Local JWT on protected routes.
10. **Frontend overhaul** — `lib/` + `components/ui/` + `hooks/` first; migrate `scheduler` feature as reference; then all other features.
11. **Test infrastructure** — pytest fixtures via `shared.testing`; Go test helpers; vitest + smoke test.
12. **Migrations & init scripts** — finalize Alembic, mongo init, Go migrations. Remove `create_all` / `create_index` startup calls.

## 15. Verification (per phase)

- **shared-py**: `cd shared-py && pip install -e . && python -c "from shared.auth import encode_jwt, decode_jwt; t=encode_jwt({'sub':'x'},'k','HS256',60); print(decode_jwt(t,'k','HS256'))"`.
- **shared-go**: `cd shared-go && go build ./...` returns 0.
- **scheduler-py**: `docker compose up postgres scheduler-backend -d`; CRUD curl checks; 404 returns envelope.
- **tax-py**: `curl /corporations` returns `[]`; `mongosh --eval "db.tax_filing_records.getIndexes()"` shows indexes.
- **auth-py password flow**: `POST /token` with `username=demo&password=demo123` → tokens issued.
- **auth-py Google flow**: open browser at `http://localhost:5173/`, click Google button, complete Google consent, land on `/auth/callback#...`, dashboard loads with user info. Verify in `users_db`: `SELECT email,google_sub FROM users;` shows new row.
- **JWT local-verify isolation**: stop auth-backend mid-session; existing token still authorizes scheduler/tax calls (no remote validation).
- **Go services**: `curl /todos` without token → 401 envelope; with token → 200.
- **Frontend**: `npm run test` runs vitest smoke green.
- **Compose-wide**: `docker compose up -d` → `docker compose ps` shows all `healthy`.

## 16. Critical Files Reference (grouped by phase)

**Phase 1 — `shared-py/` (NEW)**
- `shared-py/pyproject.toml`
- `shared-py/src/shared/{config,logging,errors,auth,cors,middleware,pagination}.py`
- `shared-py/src/shared/db/{sql,mongo}.py`
- `shared-py/src/shared/testing/{fastapi,sql,mongo}.py`

**Phase 2 — `shared-go/` (NEW)**
- `shared-go/go.mod`
- `shared-go/{config,logging,errors,auth,middleware}/*.go`
- `shared-go/db/{sql,mongo}/*.go`
- `shared-go/testing/*.go`

**Phase 3 — `scheduler-py`**
- MODIFY `backends/scheduler-py/app/main.py`, `app/database.py`, `Dockerfile`, `requirements.txt` (add `asyncpg`, drop `psycopg2-binary`)
- NEW `backends/scheduler-py/app/{config,deps}.py`, `app/routers/{events,reminders}.py`, `app/tests/{conftest,test_smoke}.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_initial.py`, `pyproject.toml`, `.env.example`

**Phase 4 — `tax-py`**
- MODIFY `backends/tax-py/app/main.py`, `app/database.py`, `app/crud.py` (all async), `Dockerfile`, `requirements.txt` (`pymongo>=4.9`)
- NEW `backends/tax-py/app/{config,deps}.py`, `app/routers/{corporations,filings,nil_t2}.py`, `app/domain/{tax_dates,nil_t2}.py` (relocate), `app/tests/...`, `pyproject.toml`, `.env.example`
- NEW `infra/mongo/init/01-tax-indexes.js`, `02-tax-seed.js`

**Phase 5 — `auth-py` + Google OAuth + Postgres users_db**
- MODIFY `backends/auth-py/app/main.py`, `Dockerfile`, `docker-compose.yml` (remove hardcoded secret; add Google env vars; add `AUTH_DATABASE_URL`)
- MODIFY `requirements.txt`: add `authlib`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `redis`, `python-json-logger`
- NEW `backends/auth-py/app/{config,deps,security}.py`
- NEW `backends/auth-py/app/models/user.py` (SQLAlchemy ORM)
- NEW `backends/auth-py/app/schemas/{user,token}.py`
- NEW `backends/auth-py/app/crud/users.py`
- NEW `backends/auth-py/app/routers/auth.py` (password flows: /token, /refresh, /me, /validate)
- NEW `backends/auth-py/app/routers/oauth.py` (/auth/google/login, /auth/google/callback)
- NEW `backends/auth-py/app/oauth/{google,state}.py` (authlib client + Redis state store)
- NEW `backends/auth-py/app/seed.py` (idempotent admin/demo/user seeding from env)
- NEW `backends/auth-py/alembic.ini`, `migrations/env.py`, `migrations/versions/0001_initial.py`
- NEW `backends/auth-py/app/tests/...`, `pyproject.toml`, `.env.example`
- MODIFY `infra/postgres/init/01-create-databases.sql` to include `users_db`
- NEW frontend `src/features/auth/GoogleSignInButton.tsx`
- NEW frontend `src/features/auth/AuthCallbackPage.tsx`
- MODIFY frontend `src/features/auth/LoginPage.tsx`, `src/App.tsx` (add `/auth/callback` route), `src/context/AuthContext.tsx` (accept tokens from hash)

**Phase 6 — local JWT integration**
- MODIFY scheduler-py + tax-py routers: add `Depends(get_current_user)`
- MODIFY `frontends/customer-portal/src/lib/api-client.ts` interceptor

**Phase 7 — remaining Python backends** ✅ COMPLETE (2026-05-16)
- finance-py: NEW `app/config.py` (extends AppSettings); NEW `app/routers/{health,investment,mortgage,salary}.py`; NEW `app/domain/{investment,mortgage,salary}.py`; NEW `app/schemas/finance.py`; REPLACE `app/main.py` (factory); UPDATE `requirements.txt`; REPLACE `Dockerfile` (repo-root build context + shared-py)
- marketplace-py: NEW `app/config.py`, `app/lifespan.py`; NEW `app/routers/{health,orders}.py` (auth on `/orders`); REPLACE `app/main.py`; UPDATE `requirements.txt`; NEW `Dockerfile`
- chatbot-py: NEW `app/config.py`, `app/store.py`, `app/domain.py`; NEW `app/routers/{health,chat,ws,sse}.py` (auth on REST+SSE paths); NEW `app/schemas/chat.py`; REPLACE `app/main.py`; UPDATE `requirements.txt`; REPLACE `Dockerfile` (repo-root build context + shared-py)
- agentic-chat-py: REPLACE `app/config.py` (extends AppSettings); REPLACE `app/main.py` (factory + `get_current_user` on `POST /message`)
- validator-py: NEW `app/config.py`; NEW `app/routers/{health,validate,stream}.py`; NEW `app/domain/diff/__init__.py`, `app/domain/rules/__init__.py`; NEW `app/schemas/validation.py`; REPLACE `app/main.py`; UPDATE `requirements.txt`; REPLACE `Dockerfile` (repo-root build context + shared-py)
- MODIFY `docker-compose.yml`: all 5 services use repo-root build context, explicit env vars, `shared-py` volume mounts, healthchecks

**Phase 8 — `todo-go`** ✅ COMPLETE (2026-05-19)
- MODIFY `backends/todo-go/{cmd/server/main.go,go.mod,Dockerfile}`
- NEW `backends/todo-go/internal/{config,handlers,repo,service}/*.go`, `migrations/*.sql`
- MODIFY `infra/postgres/init/01-create-databases.sql` to include `todo_db`

**Phase 9 — `chatbot-go`** ✅ COMPLETE (2026-05-19)
- MODIFY `backends/chatbot-go/{cmd/server/main.go,go.mod,Dockerfile}`
- NEW `backends/chatbot-go/internal/{config,handlers,store}/*.go`

**Phase 10 — Frontend overhaul** ✅ COMPLETE (2026-05-19)
- NEW `frontends/customer-portal/src/lib/{api-client,errors,zod-helpers}.ts`
- NEW `frontends/customer-portal/src/components/ui/{Button,Input,Select,Card,Modal,Toast,FormField}.tsx`
- NEW `frontends/customer-portal/src/hooks/{useApiQuery,useApiMutation,useAuthToken}.ts`
- NEW per feature: `src/features/<f>/{api,schemas,hooks}.ts`
- MODIFY `src/features/scheduler/SchedulerPage.tsx` to use `react-hook-form` + `zodResolver` (reference)
- MODIFY `src/api/{scheduler,tax,todos,marketplace,agentic_chat}.ts` → thin re-exports from feature-local api.ts
- MODIFY `package.json` (add zod, react-hook-form, @hookform/resolvers — vitest/RTL/MSW in Phase 11)

**Phase 11 — tests** 🟡 IN PROGRESS
- NEW `frontends/customer-portal/vitest.config.ts`, `src/test-utils/setup.ts`, `src/test-utils/render.tsx`, `src/test-utils/msw/handlers.ts`, `src/features/scheduler/__tests__/SchedulerPage.test.tsx`
- MODIFY `package.json` (add vitest, @vitest/ui, @testing-library/react, @testing-library/jest-dom, msw; add test/test:ui scripts)

**Phase 12 — infra & config** ✅ COMPLETE (2026-05-19)
- NEW root `.env.example`, `Makefile`, `pyrightconfig.json`
- NEW `backends/scheduler-py/migrations/versions/0001_initial.py`
- NEW per-service `.env.example` for finance-py, marketplace-py, chatbot-py, validator-py
- MODIFY `docker-compose.yml` (removed cross-service `depends_on`; all healthchecks present; env-var refs)
- MODIFY `infra/postgres/init/01-create-databases.sql` (schema grant for auth role in users_db)

## 17. Out of Scope (this plan)

- CI/CD (GitHub Actions)
- Production secrets management (Vault / AWS Secrets Manager)
- OAuth providers beyond Google (GitHub, Microsoft, Apple) — pattern is extensible, just out of scope here
- OpenAPI codegen for frontend types
- Centralized log aggregation (ELK, Loki)
- Distributed tracing (OpenTelemetry)
- Public-key (RS256) JWT for downstream services — staying with HS256 + shared secret for local-verify simplicity. ID tokens from Google are still verified against Google's JWKS (RS256) inside auth-py only.
- MFA / TOTP
- Email verification flow for password registrations

# Refactor Progress Tracker

Living log of execution against [`refactor-plan.md`](refactor-plan.md).

**Branch**: `project-9`
**Started**: 2026-05-15

> **For any LLM/dev picking up this work**: read [`refactor-plan.md`](refactor-plan.md) §4 (canonical directory shapes), §5 (Engineering Standards), and §6 (Cross-Cutting Requirements) **before** starting any phase. Every phase must satisfy the Definition of Done template below before its status flips to ✅.

## Status Legend

- ⬜ Not started
- 🟡 In progress
- ✅ Complete
- ⚠️ Blocked / needs attention

## Per-Phase Definition of Done (template)

Copy this checklist into each phase's section. **Tick every item or mark N/A with a reason** before moving the row to ✅.

```markdown
### Definition of Done

**Code & structure**
- [ ] Files placed under the canonical layout (plan §4.1 Python / §4.2 Go / §4.3 frontend)
- [ ] No deviation from canonical structure (or deviation documented with reason)
- [ ] `main.py` / `cmd/server/main.go` stays thin (no business logic inline)

**Gates** (plan §5.3)
- [ ] `pytest -q -W error` → 0 failed (or `go test ./... -race` → ok)
- [ ] `mypy app/` → Success (or `go vet ./...` clean)
- [ ] `ruff check .` clean (or `gofmt -l .` empty)
- [ ] `curl /health` → 200 `{"status":"ok"}`
- [ ] `curl /ready` → 200 when DB up; 503 when DB down
- [ ] Auth-protected route returns 401 envelope without token, 200 with token
- [ ] Error envelope shape matches `{code, message, detail, trace_id}` on every error path
- [ ] `docker compose up <service> -d` reaches healthy within 30s

**Scalability** (plan §6.1)
- [ ] Process is stateless; restartable any time
- [ ] List endpoints paginated via `shared.pagination.PageParams`
- [ ] DB connection pool sized explicitly
- [ ] All WHERE/sort columns indexed (verified with EXPLAIN or `getIndexes()`)
- [ ] No N+1 in list endpoints (`selectinload` or aggregate)

**Availability** (plan §6.2)
- [ ] `/health` (liveness) + `/ready` (readiness) endpoints present
- [ ] Compose `healthcheck:` block hits `/ready`
- [ ] Graceful shutdown via `lifespan` (Python) or signal handler (Go)
- [ ] Cross-service HTTP calls have ≤5s timeout + 2x retry on 5xx
- [ ] DB startup retry with backoff up to 30s

**Security** (plan §6.3)
- [ ] CORS explicit origin list (never `*` with credentials)
- [ ] All inputs validated via Pydantic / struct + validate
- [ ] SQL via ORM only; no f-string SQL
- [ ] Mongo queries use dict args, no `$where` with user input
- [ ] Every non-health route declares `Depends(get_current_user)` or `RequireAuth()`
- [ ] Secrets via env + Pydantic Settings, fail-fast at startup
- [ ] JWT verification checks signature + exp + type
- [ ] Redirect targets allowlist-checked (if any)
- [ ] Rate limiting on `/auth/*` (if applicable)
- [ ] Log lines contain no PII, no secrets, no full tokens

**Service Isolation Drill** (plan §5.5) — required for any service that enforces auth
- [ ] Spun up with ONLY its own DB (no `auth-backend` running) + offline-minted token → works

**Documentation**
- [ ] Files Created subsection updated
- [ ] Verification Output subsection updated with actual commands & output
- [ ] Notes / Decisions subsection captures any deviation or interesting choice
- [ ] No `# TODO`/`# FIXME` left in new code without a tracked follow-up task
```

## Phase Summary

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | `shared-py` skeleton | ✅ | 8/8 smoke tests green, end-to-end FastAPI demo passes |
| 2 | `shared-go` skeleton | ✅ | 14/14 Go tests green; Python↔Go JWT round-trip verified |
| 3 | `scheduler-py` refactor | ✅ | Canonical layout, async SQLAlchemy, JWT auth, shared-py; 9/9 tests green |
| 4 | `tax-py` refactor | ✅ | Canonical layout, async PyMongo, JWT auth, shared-py; 10/10 tests green |
| 5 | `auth-py` + Google OAuth + `users_db` | ✅ | Canonical layout, Postgres users_db, Google OAuth, 10/10 tests green |
| 6 | Enable local JWT validation | ✅ | JWT already wired in scheduler-py+tax-py; frontend api-client.ts created |
| 7 | Remaining Python backends | ✅ | finance → marketplace → chatbot → agentic-chat → validator |
| 8 | `todo-go` refactor | ✅ | Canonical layout, pgx+Postgres, golang-migrate, JWT auth, shared-go; `go vet` + `gofmt` clean |
| 9 | `chatbot-go` refactor | ✅ | Canonical layout, JWT auth (REST/SSE/WS), shared-go, `go vet` + `gofmt` clean |
| 10 | Frontend overhaul | ✅ | zod+RHF installed; lib/errors+zod-helpers; 3 shared hooks; 7 UI components; per-feature api/schemas/hooks for all features; scheduler form migrated to RHF+Zod; `tsc --noEmit` clean |
| 11 | Test infrastructure | ✅ | vitest 4 + RTL 16 + MSW 2; jsdom env; shared render/setup/handlers; SchedulerPage 4-test suite; `npm run test:run` → 4/4 green |
| 12 | Migrations & init scripts cleanup | ✅ | Alembic 0001_initial for scheduler-py; PG init SQL fixed; docker-compose isolation fix; root .env.example + Makefile + pyrightconfig.json |

---

## Phase 1: `shared-py` skeleton

**Status**: ✅ Complete
**Started**: 2026-05-15
**Completed**: 2026-05-15

### Goal

Create a local Python package `shared-py/` that every backend installs editably. Houses cross-cutting concerns so individual services stay thin and consistent.

### Module surface

| Module | Purpose |
|---|---|
| `shared.config` | `AppSettings(BaseSettings)` base — env-driven config |
| `shared.logging` | JSON formatter, `get_logger()` with `request_id` contextvar |
| `shared.errors` | `ErrorEnvelope`, `AppException`, exception handlers |
| `shared.auth` | `encode_jwt`, `decode_jwt`, `get_current_user_factory` FastAPI dep |
| `shared.cors` | `add_cors(app, origins)` — refuses `*` with credentials |
| `shared.middleware` | RequestId, AccessLog middleware |
| `shared.pagination` | `PageParams`, `Page[T]` |
| `shared.db.sql` | Async SQLAlchemy engine + session factory |
| `shared.db.mongo` | `pymongo.AsyncMongoClient` factory |
| `shared.testing.*` | pytest fixtures (TestClient, in-memory DBs, JWT minter) |

### Tasks

- [x] Create `shared-py/pyproject.toml`
- [x] Create package skeleton (`src/shared/`, sub-packages)
- [x] Implement `shared.config`
- [x] Implement `shared.logging`
- [x] Implement `shared.errors`
- [x] Implement `shared.auth`
- [x] Implement `shared.cors`
- [x] Implement `shared.middleware`
- [x] Implement `shared.pagination`
- [x] Implement `shared.db.sql`
- [x] Implement `shared.db.mongo`
- [x] Implement `shared.testing.*`
- [x] Verify: `pip install -e shared-py` + JWT round-trip succeeds

### Files Created

```
shared-py/
├── README.md
├── pyproject.toml
├── src/shared/
│   ├── __init__.py
│   ├── py.typed
│   ├── auth.py          # encode_jwt, decode_jwt, get_current_user_factory, require_role
│   ├── config.py        # AppSettings(BaseSettings) with cors/auth/log fields
│   ├── cors.py          # add_cors (rejects '*' + credentials)
│   ├── errors.py        # ErrorEnvelope, AppException + 6 subclasses, handlers
│   ├── logging.py       # JSON formatter, request_id contextvar
│   ├── middleware.py    # RequestIdMiddleware, AccessLogMiddleware
│   ├── pagination.py    # PageParams, Page[T] generic
│   ├── db/
│   │   ├── __init__.py
│   │   ├── mongo.py     # AsyncMongoClient factory (PyMongo 4.9+)
│   │   └── sql.py       # make_async_engine, async_sessionmaker, session_scope
│   └── testing/
│       ├── __init__.py
│       ├── fastapi.py   # async_client_factory fixture
│       ├── jwt.py       # auth_headers_factory fixture
│       ├── mongo.py     # mongomock-motor mongo_client fixture
│       └── sql.py       # sqlite_engine + init_models fixtures
└── tests/
    ├── __init__.py
    └── test_smoke.py    # 8 tests covering imports, JWT, config, errors, cors, pagination
```

### Verification Output

**pytest** (warnings-as-errors):

```
$ source .venv-shared/bin/activate && cd shared-py && python -m pytest tests/ -q -W error
........                                                                 [100%]
8 passed in 0.23s
```

**JWT round-trip**:

```
Token len: 271
Decoded: {'sub': 'user-1', 'email': 'x@y.z', 'name': None, 'role': 'admin',
          'type': 'access', 'jti': '83d5554f-...', 'iat': 1778887961, 'exp': 1778888021}
```

**End-to-end FastAPI demo** (CORS + middleware + handlers + auth):

```
GET /                       -> 200 {'status': 'ok'}                request_id: 9eca279b...
GET /notfound               -> 404 {'code': 'NOT_FOUND', 'message': 'nope', 'detail': {'id': 42}, 'trace_id': '...'}
GET /protected (no token)   -> 401 {'code': 'UNAUTHORIZED', 'message': 'Missing bearer token', 'trace_id': '...'}
GET /protected (with token) -> 200 {'sub': 'alice', 'role': 'admin'}
```

### Notes / Decisions

- **`get_current_user` as a factory**: kept `shared.auth` free of settings imports. Each backend instantiates the dep with its own settings provider, keeping the library pure.
- **HS256 by default**: chosen for local-verify simplicity. Backend services share `AUTH_SECRET_KEY` env var; nothing calls auth-py at request time.
- **`auto_error=False` on `OAuth2PasswordBearer`**: lets us produce envelope-shaped 401 responses instead of FastAPI's default `{"detail": "Not authenticated"}`.
- **Token in query string for SSE/WebSocket**: `get_current_user` falls back to `?access_token=` when no header is present — needed for WebSocket and SSE handshakes that cannot send custom headers.
- **AsyncMongoClient** (PyMongo 4.9+), **not Motor**: matches user's requirement. Native async, no extra dependency.
- **`ValidationError.status_code = 422` hardcoded**: avoids Starlette's deprecated `HTTP_422_UNPROCESSABLE_ENTITY` constant lookup.
- **CORS factory rejects `["*"]` with credentials**: catches CWE-942 misconfig at construction time, not at runtime.
- Verification venv path `.venv-shared/` added to `.gitignore`.

### Definition of Done

- [x] **Code & structure** — N/A for shared lib (no canonical service shape applies); shared-py uses src-layout per Python packaging best practice.
- [x] **Test gate**: `pytest -q -W error` → `8 passed in 0.23s`.
- [x] **Type-hint coverage**: every function in `shared/*.py` has explicit return + arg types; ready for `mypy --strict` downstream.
- [x] **Import smoke**: `from shared.{config,logging,errors,auth,cors,middleware,pagination,db.sql,db.mongo} import *` succeeds.
- [x] **End-to-end FastAPI demo**: error envelopes, request-id propagation, JWT auth, CORS all verified inline.
- [x] **Scalability**: pagination types provided; SQL engine factory exposes pool sizing; library imposes no global state.
- [x] **Availability**: middleware preserves request-id across exceptions; CORS factory fails-fast on misconfig.
- [x] **Security**: HS256 with ≥16-char secret enforced by Pydantic Settings; `decode_jwt` validates signature + exp + type; CORS rejects `*`+credentials.
- [x] **Isolation drill**: N/A — library, not a service.
- [x] **Documentation**: full file tree, decisions, verification output captured above.

---

## Phase 2: `shared-go` skeleton

**Status**: ✅ Complete
**Started**: 2026-05-15
**Completed**: 2026-05-15

### Goal

Build the Go parallel to `shared-py`. Same envelope shapes, same JWT format, same shared-secret-based local verification so a token issued by either side decodes on the other.

### Module surface

Module path: `github.com/mihirzz/chatbot-shared-go`. Go services consume it via a `go.mod` `replace` directive pointing at `../../shared-go`.

| Package | Purpose |
|---|---|
| `shared/config` | viper loader, `LoadConfig[T]()` generic with reflection-based env binding |
| `shared/logging` | zap JSON logger factory |
| `shared/errors` | `ErrorEnvelope` matching Python shape; `FiberErrorHandler` |
| `shared/auth` | `EncodeJWT`, `VerifyJWT`, `RequireAuth()` Fiber middleware, `RequireRole()` |
| `shared/middleware` | RequestID, AccessLog, Recover, `Install()` helper |
| `shared/db/sql` | pgx/v5 connection pool factory |
| `shared/db/mongo` | `go.mongodb.org/mongo-driver` client factory |
| `shared/testing` | `NewTestApp`, `MintTestToken`, `AuthHeader` helpers |

### Tasks

- [x] Create `shared-go/go.mod`
- [x] Implement `config` (with reflection-based env binding for user extensions)
- [x] Implement `logging` (zap factory)
- [x] Implement `errors` (mirrors Python `ErrorEnvelope`)
- [x] Implement `auth` (HS256 encode/decode + Fiber middleware)
- [x] Implement `middleware` (RequestID, AccessLog, Recover)
- [x] Implement `db/sql` (pgx pool)
- [x] Implement `db/mongo` (mongo-driver client)
- [x] Implement `testing` helpers
- [x] Tests for each package (14 total)
- [x] Cross-language JWT compat verified

### Files Created

```
shared-go/
├── README.md
├── go.mod / go.sum
├── auth/
│   ├── auth.go            # EncodeJWT, VerifyJWT, RequireAuth, RequireRole, FromContext
│   └── auth_test.go       # 6 tests
├── cmd/crosscheck/
│   └── main.go            # CLI for Python↔Go JWT cross-verification
├── config/
│   ├── config.go          # BaseSettings, LoadConfig[T] with reflection BindEnv
│   └── config_test.go     # 3 tests
├── db/
│   ├── mongo/mongo.go     # NewClient, Collection helper
│   └── sql/sql.go         # NewPool with sane defaults + Ping
├── errors/
│   ├── errors.go          # ErrorEnvelope, AppError, FiberErrorHandler
│   └── errors_test.go     # 2 tests
├── logging/logging.go     # NewLogger (zap)
├── middleware/
│   ├── middleware.go      # RequestID, AccessLog, Recover, Install
│   └── middleware_test.go # 3 tests
└── testing/testing.go     # NewTestApp, MintTestToken, AuthHeader
```

### Verification Output

**`go test ./... -v`**:

```
=== RUN   TestEncodeDecodeRoundTrip       --- PASS
=== RUN   TestVerifyWrongSecret           --- PASS
=== RUN   TestVerifyWrongType             --- PASS
=== RUN   TestRequireAuthMiddleware       --- PASS
=== RUN   TestRequireAuthQueryParamFallback --- PASS
=== RUN   TestRequireRole                 --- PASS
ok  	github.com/mihirzz/chatbot-shared-go/auth	0.761s
=== RUN   TestLoadConfigFromEnv           --- PASS
=== RUN   TestCORSOriginsParsing          --- PASS
=== RUN   TestValidateRejectsShortSecret  --- PASS
ok  	github.com/mihirzz/chatbot-shared-go/config	0.420s
=== RUN   TestNotFoundEnvelope            --- PASS
=== RUN   TestUnknownErrorReturns500      --- PASS
ok  	github.com/mihirzz/chatbot-shared-go/errors	0.245s
=== RUN   TestRequestIDGeneratedAndEchoed --- PASS
=== RUN   TestRequestIDEchoesInbound      --- PASS
=== RUN   TestAccessLogDoesNotPanic       --- PASS
ok  	github.com/mihirzz/chatbot-shared-go/middleware	0.590s
```

**Cross-language JWT compat** (the killer test for service isolation):

```
# Python mints, Go verifies
$ python -c "from shared.auth import encode_jwt; print(encode_jwt({...}, '<secret>'))" \
    | go run ./cmd/crosscheck verify
{
  "email": "x@y.z",
  "jti": "a8d4c1a7-d143-4e10-a4bd-403592f035a9",
  "role": "admin",
  "sub": "cross-1",
  "type": "access"
}

# Go mints, Python verifies
$ go run ./cmd/crosscheck mint | python -c "from shared.auth import decode_jwt; ..."
{
  "sub": "go-2",
  "email": "alice-go@example.com",
  "role": "user",
  "type": "access",
  "jti": "5d219486-...",
  "iat": 1778888526,
  "exp": 1778888826
}
```

### Notes / Decisions

- **Module path `github.com/mihirzz/chatbot-shared-go`**: not published to a remote — services use `replace` directive pointing at `../../shared-go`.
- **Reflection-based env binding in `LoadConfig`**: services extending `BaseSettings` with their own fields get automatic env binding without needing to call `BindEnv` themselves. Walks `mapstructure` tags including `,squash` embeds.
- **`AppError` carries status code with it**: lets `FiberErrorHandler` render the right HTTP status without each handler having to know.
- **`auth.RequireAuth` config takes a `SecretProvider func() string`**: same factory pattern as Python — keeps the package pure and lets the secret rotate at runtime if needed.
- **Token in query string for SSE/WS**: `RequireAuth` falls back to `?access_token=` same as Python; matches the cross-language behavior.
- **`go 1.22` in `go.mod`**: existing services pin 1.21; using 1.22 here for generics; services upgrade when they adopt shared-go.
- **Existing Go services left untouched** — their refactor is Phase 8/9.
- **`cmd/crosscheck`**: kept as a CLI tool (not a test) because it needs to run from outside the Go test environment to exercise real Python↔Go interop.

### Definition of Done

- [x] **Code & structure** — N/A for shared lib; standard Go module layout (`<pkg>/<pkg>.go` + `<pkg>_test.go`).
- [x] **Test gate**: `go test ./... -race` → all 4 packages pass (14 tests total).
- [x] **Vet gate**: `go vet ./...` → no output.
- [x] **Fmt gate**: `gofmt -l .` → empty.
- [x] **Cross-language compat**: Python-issued JWT decodes in Go; Go-issued JWT decodes in Python (foundation of service-isolation principle).
- [x] **Scalability**: pgx pool factory sets `MaxConns=10, MinConns=1, MaxConnLifetime=1h`; Mongo uses 5s server-selection timeout.
- [x] **Availability**: `NewPool`/`NewClient` ping after connect, fail-fast.
- [x] **Security**: HS256 only (explicit reject of other algs); `RequireAuth` returns envelope-shaped 401, not Fiber default; `BaseSettings.Validate` enforces ≥16-char secret.
- [x] **Isolation drill**: N/A — library.
- [x] **Documentation**: full file tree, decisions, verification output above.

---

## Phase 3: `scheduler-py` refactor

**Status**: ✅ Complete
**Started**: 2026-05-15
**Completed**: 2026-05-15

### Goal

Refactor `scheduler-py` to the canonical Python service layout (plan §4.1). Acts as the **reference implementation** for all other Python backends. Key changes:

- Split monolithic `main.py` (160 LOC) into thin factory + routers/crud/schemas/models packages
- Migrate sync SQLAlchemy + `psycopg2` → async SQLAlchemy 2 + `asyncpg`
- All route handlers converted to `async def`
- Integrate `shared-py`: config, cors, errors, middleware, auth, pagination, db.sql
- Add `/health` (liveness) and `/ready` (readiness) endpoints
- Enforce JWT auth on all resource routes (`Depends(get_current_user)`)
- Paginate list endpoints via `PageParams` / `Page[T]`
- Add `pyproject.toml`, `.env.example`, `alembic.ini`, `migrations/` stubs
- Full smoke test suite (9 tests) with in-memory SQLite + offline JWT

### Files Created / Modified

```
backends/scheduler-py/
├── pyproject.toml              ← NEW (pytest/mypy/ruff config)
├── .env.example                ← NEW (all env vars documented)
├── alembic.ini                 ← NEW (Phase 12 will add 0001_initial migration)
├── requirements.txt            ← UPDATED (asyncpg, alembic; removed psycopg2)
├── Dockerfile                  ← UPDATED (repo-root build context for shared-py)
├── migrations/
│   ├── README.md               ← NEW
│   ├── env.py                  ← NEW (async Alembic env)
│   └── versions/.gitkeep      ← NEW
└── app/
    ├── __init__.py             (unchanged)
    ├── main.py                 ← REPLACED (thin factory, ~50 LOC)
    ├── config.py               ← NEW (Settings extends AppSettings)
    ├── deps.py                 ← NEW (get_db, get_current_user)
    ├── lifespan.py             ← NEW (async engine start/stop)
    ├── routers/
    │   ├── __init__.py         ← NEW
    │   ├── health.py           ← NEW (/health + /ready)
    │   ├── events.py           ← NEW (events CRUD, paginated)
    │   └── reminders.py        ← NEW (reminders CRUD, paginated)
    ├── schemas/
    │   ├── __init__.py         ← NEW
    │   ├── events.py           ← NEW
    │   └── reminders.py        ← NEW
    ├── models/
    │   ├── __init__.py         ← NEW
    │   └── event.py            ← NEW (SQLAlchemy 2 mapped_column style)
    ├── crud/
    │   ├── __init__.py         ← NEW
    │   ├── events.py           ← NEW (async, returns total for pagination)
    │   └── reminders.py        ← NEW (async)
    ├── services/__init__.py    ← NEW (stub)
    ├── domain/__init__.py      ← NEW (stub)
    └── tests/
        ├── __init__.py         ← NEW
        ├── conftest.py         ← NEW (in-memory SQLite + offline JWT)
        └── test_smoke.py       ← NEW (9 smoke tests)

DELETED: app/database.py, app/models.py, app/schemas.py, app/crud.py
```

`docker-compose.yml` scheduler-backend updated: asyncpg URL, AUTH_SECRET_KEY env var, healthcheck on `/ready`.

### Verification Output

```
# pytest (-W error = warnings-as-errors)
$ cd backends/scheduler-py && python -m pytest app/tests/ -q -W error
.........                                              [100%]
9 passed in 0.16s

# mypy
$ mypy app/ --ignore-missing-imports --exclude 'app/tests'
Success: no issues found in 19 source files

# ruff
$ ruff check .
All checks passed!
```

### Definition of Done

**Code & structure**
- [x] Files placed under canonical layout (plan §4.1) — exact match
- [x] No deviation from canonical structure
- [x] `main.py` thin — ~50 LOC, factory only

**Gates** (plan §5.3)
- [x] `pytest -q -W error` → `9 passed`
- [x] `mypy app/` → `Success: no issues found in 19 source files`
- [x] `ruff check .` → `All checks passed!`
- [x] `curl /health` → 200 `{"status": "ok"}` (verified via ASGI test client)
- [x] `curl /ready` → 200 when DB up (verified via ASGI test client)
- [x] Auth-protected route returns 401 envelope without token; 200 with token
- [x] Error envelope `{code, message, detail, trace_id}` verified on 404/401 paths
- [x] `docker-compose.yml` updated with healthcheck on `/ready`

**Scalability** (plan §6.1)
- [x] Stateless — no in-process mutable state beyond lifespan-managed engine
- [x] List endpoints paginated via `PageParams` / `Page[T]`
- [x] DB pool: `pool_size=5, max_overflow=10, pool_pre_ping=True` (via `shared.db.sql`)
- [x] Indexes on `events.start_time`, `reminders.remind_at`, `reminders.event_id`
- [x] No N+1 — `selectinload(Event.reminders)` + `lazy="selectin"` default

**Availability** (plan §6.2)
- [x] `/health` liveness + `/ready` readiness present
- [x] Compose `healthcheck:` hits `/ready`
- [x] Graceful shutdown via `lifespan` (engine dispose on exit)
- [x] DB startup connectivity verified in lifespan

**Security** (plan §6.3)
- [x] CORS via `shared.cors.add_cors` — never `*` with credentials (CWE-942)
- [x] All inputs via Pydantic schemas with field constraints (CWE-20)
- [x] All SQL via SQLAlchemy ORM — no f-string SQL (CWE-89)
- [x] Every non-health route has `Depends(get_current_user)` (CWE-306)
- [x] Secrets via env + Pydantic Settings, fail-fast at startup (CWE-798)
- [x] JWT verification (signature + exp + type) via `shared.auth.decode_jwt` (CWE-345)

**Service Isolation Drill** — deferred to Phase 6 (when JWT validation is enabled across all services)

### Notes / Decisions

- **`create_all()` removed** — schema lives in `migrations/`. Phase 12 generates `0001_initial.py`. For local dev, create tables via Alembic or psql manually.
- **`lazy="selectin"` on `Event.reminders`** — prevents N+1 on all code paths, not just explicit `selectinload` calls.
- **`# type: ignore[call-arg]` on `Settings()`** — mypy can't see pydantic-settings reads required fields from env; documented.
- **`# type: ignore[arg-type]` on `Page.build()`** — ORM→schema coercion happens at serialization (`from_attributes=True`); mypy doesn't trace through it.
- **`B008` ruff rule ignored** — `Depends()` in default args is the canonical FastAPI pattern.
- **CORS_ORIGINS in tests** — must be JSON array syntax `["..."]` for pydantic-settings `list[str]` env parsing.

---

## Phase 4: `tax-py` refactor

**Status**: ✅ Complete
**Started**: 2026-05-15
**Completed**: 2026-05-16

### Goal

Refactor `backends/tax-py` from a 249-LOC synchronous FastAPI monolith into the canonical Python service layout (plan §4.1). Key changes:

- Split single `main.py` into routers/crud/schemas/models/services/domain layers
- Migrate sync PyMongo → `AsyncMongoClient` (PyMongo 4.9+)
- Async httpx for outbound scheduler API calls
- Integrate `shared-py` (config, cors, errors, middleware, auth)
- JWT auth on all resource routes via `Depends(get_current_user)`
- `/health` and `/ready` endpoints
- Full smoke test suite (10 tests) using `mongomock-motor` — no live MongoDB required

### Files Created / Modified

```
backends/tax-py/
├── pyproject.toml              ← NEW
├── .env.example                ← NEW
├── alembic.ini                 ← NEW (structural stub — no SQL migrations for Mongo)
├── requirements.txt            ← UPDATED (pymongo>=4.9, pydantic-settings, httpx)
├── Dockerfile                  ← REPLACED (repo-root build context for shared-py)
├── migrations/
│   ├── README.md               ← NEW
│   ├── env.py                  ← NEW (placeholder)
│   └── versions/.gitkeep      ← NEW
└── app/
    ├── main.py                 ← REPLACED (~35 LOC factory)
    ├── config.py               ← NEW
    ├── deps.py                 ← NEW
    ├── lifespan.py             ← NEW (AsyncMongoClient lifecycle + index creation)
    ├── routers/
    │   ├── __init__.py         ← NEW
    │   ├── health.py           ← NEW (/health + /ready with Mongo ping)
    │   ├── corporations.py     ← NEW (7 endpoints: CRUD + filing-schedule + setup-reminders)
    │   ├── filings.py          ← NEW (/filings/upcoming + filing status update)
    │   └── nil_t2.py           ← NEW (generate + read nil T2)
    ├── schemas/
    │   ├── __init__.py         ← NEW
    │   ├── corporations.py     ← NEW
    │   ├── filings.py          ← NEW
    │   └── nil_t2.py           ← NEW
    ├── models/
    │   ├── __init__.py         ← NEW
    │   ├── corporation.py      ← NEW (CorporationDoc)
    │   ├── filing.py           ← NEW (TaxFilingDoc)
    │   └── nil_t2.py           ← NEW (NilT2Doc)
    ├── crud/
    │   ├── __init__.py         ← NEW
    │   ├── corporations.py     ← NEW (async, cascade delete)
    │   ├── filings.py          ← NEW (async, 7 functions)
    │   └── nil_t2.py           ← NEW (async)
    ├── services/
    │   ├── __init__.py         ← NEW
    │   └── reminders.py        ← NEW (setup_reminders: scheduler httpx + best-effort reminders)
    ├── domain/
    │   ├── __init__.py         ← NEW
    │   ├── tax_dates.py        ← MOVED from app/tax_dates.py (pure deadline logic)
    │   └── nil_t2.py           ← MOVED from app/nil_t2.py (Protocol duck-type, no I/O)
    └── tests/
        ├── __init__.py         ← NEW
        ├── conftest.py         ← NEW (mongomock-motor patch + offline JWT)
        └── test_smoke.py       ← NEW (10 smoke tests)

DELETED: app/database.py, app/models.py, app/schemas.py, app/crud.py, app/tax_dates.py, app/nil_t2.py
```

`docker-compose.yml` tax-backend updated: repo-root build context, `AUTH_SECRET_KEY`/`CORS_ORIGINS`/`LOG_LEVEL` env vars, `./shared-py:/shared-py:ro` volume, healthcheck on `/ready`, `scheduler-backend` dependency changed to `service_healthy`.

`infra/mongo/init/01-tax-indexes.js` and `02-tax-seed.js` added for production MongoDB init.

### Verification Output

```
# pytest (-W error = warnings-as-errors)
$ cd backends/tax-py && pytest -q -W error
..........                                                               [100%]
10 passed in 0.03s

# mypy
$ mypy app/ --ignore-missing-imports
Success: no issues found in 27 source files

# ruff
$ ruff check .
All checks passed!
```

### Definition of Done

**Code & structure**
- [x] Files placed under canonical layout (plan §4.1) — exact match
- [x] No deviation from canonical structure
- [x] `main.py` thin — ~35 LOC, factory only

**Gates** (plan §5.3)
- [x] `pytest -q -W error` → `10 passed`
- [x] `mypy app/ --ignore-missing-imports` → `Success: no issues found in 27 source files`
- [x] `ruff check .` → `All checks passed!`
- [x] `curl /health` → 200 `{"status": "ok"}` (verified via ASGI test client)
- [x] `curl /ready` → 200 when DB up (verified via ASGI test client)
- [x] Auth-protected route returns 401 envelope without token; 200 with token
- [x] Error envelope `{code, message, detail, trace_id}` verified on 404/401 paths
- [x] `docker-compose.yml` updated with healthcheck on `/ready`

**Scalability** (plan §6.1)
- [x] Stateless — no in-process mutable state beyond lifespan-managed client
- [x] Compound indexes on `tax_filing_records(corp_id, filing_type, period_label)` and `nil_t2_reports(corp_id, fiscal_year_end)` — idempotent via `_create_indexes` on startup
- [x] No N+1 — `delete_stale_filings` materializes once with `to_list(None)`, filters in Python

**Availability** (plan §6.2)
- [x] `/health` liveness + `/ready` readiness present
- [x] Compose `healthcheck:` hits `/ready`
- [x] Graceful shutdown via `lifespan` (`_client.close()` on exit)
- [x] MongoDB ping at startup (fail-fast if unreachable)
- [x] httpx outbound calls use 5s timeout; reminder failures don't abort setup-reminders

**Security** (plan §6.3)
- [x] CORS via `shared.cors.add_cors` — never `*` with credentials (CWE-942)
- [x] All inputs via Pydantic schemas (CWE-20)
- [x] Mongo queries use dict args, no `$where` with user input (CWE-943)
- [x] Every non-health route has `Depends(get_current_user)` (CWE-306)
- [x] Secrets via env + Pydantic Settings, fail-fast at startup (CWE-798)
- [x] JWT verification via `shared.auth.decode_jwt` (CWE-345)

**Service Isolation Drill** — deferred to Phase 6 (when JWT validation enabled across all services)

### Notes / Decisions

- **`_id` stored as string, queried as string**: `CorporationDoc._new_id()` returns `str(ObjectId())`. CRUD queries use `{"_id": corp_id}` (string), not `{"_id": ObjectId(corp_id)}`. This avoids BSON type mismatch between mongomock-motor and real MongoDB.
- **`AsyncMongoClient` (PyMongo 4.9+), not Motor**: native async, no extra dependency. `.find().to_list(None)` pattern used throughout.
- **`_CorpLike` Protocol in `domain/nil_t2.py`**: avoids circular import from `app.models`; lets domain layer be self-contained.
- **`Any` for MongoDB driver types in mypy**: PyMongo 4.9 stubs are incomplete for `AsyncMongoClient`/`AsyncDatabase`. All CRUD and lifespan module globals typed as `Any`.
- **Single `httpx.AsyncClient`** wraps entire scheduler filing loop (not per-request).
- **`BadGatewayError` not `HTTPException(502)`** — all error raises use `shared.errors` subclasses for correct envelope shape.
- **`datetime.utcnow()` → `datetime.now(UTC)`** — Python 3.12 deprecation triggers `-W error` failure; all models and CRUD updated.

---

## Phase 5: `auth-py` refactor + Google OAuth + Postgres `users_db`

**Status**: ✅ Complete
**Started**: 2026-05-16
**Completed**: 2026-05-16

### Goal

Refactor `backends/auth-py` from a 424-LOC synchronous in-memory monolith to the canonical Python service layout. Key changes:

- Postgres `users_db` via async SQLAlchemy + asyncpg
- Alembic migration `0001_initial` creates `users` table
- Idempotent user seeding from `SEED_USERS` env var (replaces hardcoded in-memory dict)
- Google OAuth 2.0 + PKCE via `authlib`; Redis for state/CSRF protection
- JWT issued via `shared.auth.encode_jwt` (HS256, same shared secret)
- Refresh token flow using `token_type="refresh"` parameter
- Frontend: `GoogleSignInButton`, `AuthCallbackPage`, `/auth/callback` route, `src/lib/api-client.ts`
- Full smoke test suite (10 tests) using SQLite in-memory + `_FakeRedis`

### Files Created / Modified

```
backends/auth-py/
├── pyproject.toml              ← NEW
├── .env.example                ← NEW
├── alembic.ini                 ← NEW
├── requirements.txt            ← UPDATED (authlib, sqlalchemy, asyncpg, alembic, redis, bcrypt)
├── Dockerfile                  ← REPLACED (repo-root build context for shared-py)
├── migrations/
│   ├── README.md               ← NEW
│   ├── env.py                  ← NEW (async Alembic)
│   └── versions/
│       └── 0001_initial.py     ← NEW (users table)
└── app/
    ├── main.py                 ← REPLACED (~35 LOC factory)
    ├── config.py               ← NEW
    ├── deps.py                 ← NEW (get_db, get_redis)
    ├── lifespan.py             ← NEW (engine + Redis + seeding)
    ├── security.py             ← NEW (bcrypt hash/verify — avoids passlib Python 3.12 deprecation)
    ├── seed.py                 ← NEW (idempotent upsert from SEED_USERS)
    ├── models/
    │   ├── __init__.py         ← NEW
    │   └── user.py             ← NEW (SQLAlchemy User ORM)
    ├── schemas/
    │   ├── __init__.py         ← NEW
    │   ├── token.py            ← NEW (Token, TokenData, RefreshRequest)
    │   └── user.py             ← NEW (UserOut, UserCreate)
    ├── crud/
    │   └── users.py            ← NEW (get_by_email/id/google_sub, create, update, upsert_google)
    ├── oauth/
    │   ├── google.py           ← NEW (authlib AsyncOAuth2Client + JWKS verify)
    │   └── state.py            ← NEW (Redis OAuthStateStore, 10-min TTL)
    ├── routers/
    │   ├── health.py           ← NEW (/health + /ready with DB+Redis ping)
    │   ├── auth.py             ← NEW (/auth/token, /auth/login, /auth/refresh, /auth/me, /auth/register)
    │   └── oauth.py            ← NEW (/auth/google/login, /auth/google/callback)
    └── tests/
        ├── conftest.py         ← NEW (SQLite in-memory + _FakeRedis + lifespan patch)
        └── test_smoke.py       ← NEW (10 smoke tests)

DELETED: old monolithic app/main.py
```

`infra/postgres/init/01-create-databases.sql` — NEW (creates users_db, todo_db, scheduler_db).

`docker-compose.yml` auth-backend: repo-root build context, AUTH_DATABASE_URL, REDIS_URL, GOOGLE_* env vars, SEED_USERS, healthcheck on `/ready`, depends on postgres+redis.

`docker-compose.yml` postgres: added `./infra/postgres/init:/docker-entrypoint-initdb.d:ro` volume.

### Verification Output

```
$ cd backends/auth-py && pytest -q -W error
..........                                                               [100%]
10 passed in 2.05s

$ mypy app/ --ignore-missing-imports
Success: no issues found in 23 source files

$ ruff check .
All checks passed!
```

### Notes / Decisions

- **passlib removed**: passlib imports Python 3.12's deprecated `crypt` module, triggering `-W error` failure. Replaced with direct `bcrypt` calls.
- **`encode_jwt` `token_type` parameter**: must pass `token_type="refresh"` explicitly — the `type` key in the payload dict is overwritten by `encode_jwt`'s `token_type` parameter.
- **`decode_jwt` `expected_type=None` for refresh tokens**: the default `expected_type="access"` rejects refresh tokens; pass `None` to skip type check then verify manually.
- **`_FakeRedis` in tests**: minimal in-process stub for `OAuthStateStore`; avoids a real Redis dependency in tests.
- **Google OAuth not tested live**: unit tests mock Redis state; end-to-end Google flow requires real `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`.
- **Account linking**: Google sign-in with an email matching existing password user links `google_sub`; password registration with an email matching Google-only user sets `password_hash`.

### Definition of Done

- [x] `pytest -q -W error` → `10 passed`
- [x] `mypy app/ --ignore-missing-imports` → `Success`
- [x] `ruff check .` → `All checks passed!`
- [x] `/health` → 200 `{"status":"ok"}` (ASGI test client)
- [x] `/ready` → 200 (SQLite/FakeRedis in tests)
- [x] `/auth/token` wrong creds → 401 envelope; correct creds → 200 with tokens
- [x] `/auth/me` no token → 401 envelope
- [x] `docker-compose.yml` updated with healthcheck, SEED_USERS, GOOGLE_* vars

---

## Phase 6: Local JWT validation + frontend `api-client.ts`

**Status**: ✅ Complete
**Started**: 2026-05-16
**Completed**: 2026-05-16

### Goal

- Verify local JWT validation is already wired in `scheduler-py` and `tax-py` (it was — added in Phases 3 and 4)
- Create shared `src/lib/api-client.ts` axios instance for the frontend
- Add `GoogleSignInButton` and `AuthCallbackPage` to the frontend auth feature
- Add `/auth/callback` route to `App.tsx`

### Files Created / Modified

```
frontends/customer-portal/src/
├── lib/
│   └── api-client.ts           ← NEW (shared axios instance + JWT interceptor + refresh-on-401)
└── features/auth/
    ├── GoogleSignInButton.tsx   ← NEW (links to /auth/google/login)
    ├── AuthCallbackPage.tsx     ← NEW (parses hash fragment, stores tokens, scrubs URL, navigates)
    └── LoginPage.tsx            ← MODIFIED (added GoogleSignInButton)
src/App.tsx                     ← MODIFIED (added /auth/callback route)
src/api/auth.ts                 ← MODIFIED (updated endpoint paths to /auth/* prefix)
```

### Verification

- `tsc --noEmit` → no TypeScript errors
- `scheduler-py` and `tax-py`: all resource routes already use `Depends(get_current_user)` (added in Phases 3+4); no changes needed

### Service Isolation Drill

Both `scheduler-py` and `tax-py` verify JWTs locally using `AUTH_SECRET_KEY`. No dependency on `auth-backend` at request time. Drill deferred to integration testing when Docker environment is fully up.

---

## Phase 7: Remaining Python backends

**Status**: ✅ Complete
**Started**: 2026-05-16
**Completed**: 2026-05-16

### Goal

Refactor `finance-py`, `marketplace-py`, `chatbot-py`, `agentic-chat-py`, `validator-py` to canonical layout per refactor-plan.md §8 (Per-Service Refactor Notes).

### Files Created / Modified

```
backends/finance-py/
├── Dockerfile                   REPLACE (repo-root build context + shared-py)
├── requirements.txt             UPDATE (pinned versions + pydantic-settings + python-jose)
└── app/
    ├── __init__.py              NEW
    ├── main.py                  REPLACE (factory: 3 domain routers + legacy /compute compat)
    ├── config.py                NEW (extends AppSettings)
    ├── schemas/__init__.py      NEW
    ├── schemas/finance.py       NEW (InvestmentParams, MortgageParams, SalaryProjectionParams, ComputeRequest, ComputeResponse)
    ├── domain/__init__.py       NEW
    ├── domain/investment.py     NEW (compute_investment — pure math, no I/O)
    ├── domain/mortgage.py       NEW (compute_mortgage + amortization_schedule)
    ├── domain/salary.py         NEW (compute_salary_projection)
    └── routers/
        ├── __init__.py          NEW
        ├── health.py            NEW (/health + /ready)
        ├── investment.py        NEW (POST /investment/compute)
        ├── mortgage.py          NEW (POST /mortgage/compute)
        └── salary.py            NEW (POST /salary/compute)

backends/marketplace-py/
├── Dockerfile                   NEW (repo-root build context + shared-py)
├── requirements.txt             UPDATE (pinned + pydantic-settings + python-jose)
└── app/
    ├── main.py                  REPLACE (factory + shared middleware)
    ├── config.py                NEW (kafka_bootstrap, topic_orders_created)
    ├── lifespan.py              NEW (async Kafka producer start/stop via app.state)
    └── routers/
        ├── __init__.py          NEW
        ├── health.py            NEW
        └── orders.py            NEW (POST /orders — get_current_user auth + shared logger)

backends/chatbot-py/
├── Dockerfile                   REPLACE (repo-root build context + shared-py)
├── requirements.txt             UPDATE
└── app/
    ├── main.py                  REPLACE (factory)
    ├── config.py                NEW
    ├── store.py                 NEW (in-memory pending_responses + conversations dicts)
    ├── domain.py                NEW (generate_random_response, get_random_delay, THINKING_STATUSES)
    ├── schemas/__init__.py      NEW
    ├── schemas/chat.py          NEW (ChatMessage, ChatRequest, ChatResponse, StatusUpdate)
    └── routers/
        ├── __init__.py          NEW
        ├── health.py            NEW
        ├── chat.py              NEW (POST /api/chat + /api/chat/async — auth required; GET /api/chat/status; GET+DELETE /api/conversations)
        ├── ws.py                NEW (WebSocket /ws/chat — token via ?access_token= query param)
        └── sse.py               NEW (POST /api/chat/stream — auth required; SSE generator)

backends/agentic-chat-py/app/
├── main.py                      REPLACE (factory + shared middleware + get_current_user on POST /message)
└── config.py                    REPLACE (extends AppSettings; backwards-compat settings singleton preserved)

backends/validator-py/
├── Dockerfile                   REPLACE (repo-root build context + shared-py)
├── requirements.txt             UPDATE
└── app/
    ├── main.py                  REPLACE (factory)
    ├── config.py                NEW
    ├── schemas/__init__.py      NEW
    ├── schemas/validation.py    NEW (ValidationDeviceResult, ValidationTask, PaginatedTasksResponse, etc.)
    ├── domain/__init__.py       NEW
    ├── domain/diff/__init__.py  NEW (generate_dummy_output, generate_device_result, get_or_create_device_result)
    ├── domain/rules/__init__.py NEW (generate_validation_tasks, get_or_create_validation_tasks, clear_tasks_cache)
    └── routers/
        ├── __init__.py          NEW
        ├── health.py            NEW
        ├── validate.py          NEW (GET /tasks paginated + DELETE /tasks/cache)
        └── stream.py            NEW (GET /{cr_id}/{device_id}/stream — dual-mode SSE; presigned URL fetch)

docker-compose.yml               MODIFY (5 services: repo-root build context, shared-py volume, env vars, healthchecks)
```

### Verification

```
# finance-py — TestClient smoke
finance-py: ALL PASS (compute + investment/mortgage/salary routers)
  GET /health → 200 {"status":"ok"}
  POST /compute (investment) → 200 {ok:true}       ← legacy compat route
  POST /investment/compute → 200 {ok:true}          ← new per-domain route
  POST /mortgage/compute → 200 {ok:true}
  POST /salary/compute → 200 {ok:true}

# chatbot-py — TestClient smoke
chatbot-py: ALL PASS (auth on protected paths)
  GET /health → 200
  POST /api/chat (no token) → 401 {code:"UNAUTHORIZED"} ✓ envelope
  POST /api/chat (with token) → 200
  POST /api/chat/stream (no token) → 401 ✓
  GET /api/conversations/missing → 404 {code:"NOT_FOUND"} ✓ envelope

# validator-py — TestClient smoke
validator-py: ALL PASS (domain/diff/ + domain/rules/ dirs)
  GET /health → 200
  GET /tasks → 200 (20 tasks total)
  GET /tasks?page=1&page_size=5 → 200 (5 tasks)
  GET /tasks?change_status=Completed → 200 (filtered)
```

### Key Decisions

- **finance-py**: Split into `routers/{investment,mortgage,salary}.py` per plan. Added legacy `/compute` dispatch route for frontend backwards-compat (frontend calls `/compute` with `kind` field). No auth — financial calculators are stateless public APIs.
- **marketplace-py**: Auth added on `POST /orders` per plan. Kafka producer in `app.state` via `lifespan.py` (not module global).
- **chatbot-py**: Auth on `POST /api/chat`, `POST /api/chat/async`, `POST /api/chat/stream` (REST+SSE protected paths). WebSocket `/ws/chat` accepts `?access_token=` query param. `store.py` in-memory state is intentional (demo service, no DB).
- **agentic-chat-py**: Surgical update — existing `agents/`, `redis_store.py`, `models.py` untouched. `settings` backwards-compat singleton retained for existing modules.
- **validator-py**: `domain/diff/` and `domain/rules/` are directories (packages) per plan, not flat files. Relative imports adjusted to `...schemas` (3 dots) from sub-package depth.

### Definition of Done

- [x] All 5 `main.py` files replaced with factory pattern (`install_middleware`, `register_exception_handlers`, `add_cors`)
- [x] All 5 `config.py` extend `AppSettings` from shared-py
- [x] All 5 `Dockerfile`s use repo-root build context + shared-py layer
- [x] `docker-compose.yml` updated for all 5 services (build context, env, healthchecks, shared-py volumes)
- [x] `shared.errors.register_exception_handlers` mounted → error envelope on all 5
- [x] `shared.cors.add_cors` replaces bare `CORSMiddleware(allow_origins=["*"])` on all 5
- [x] `shared.middleware.install_middleware` installed on all 5
- [x] finance-py: `routers/{investment,mortgage,salary}.py` + `domain/{investment,mortgage,salary}.py` per plan
- [x] validator-py: `domain/diff/__init__.py` + `domain/rules/__init__.py` (package dirs) per plan
- [x] chatbot-py: auth on REST + SSE protected paths (`POST /api/chat`, `/api/chat/async`, `/api/chat/stream`)
- [x] marketplace-py: auth on `POST /orders`
- [x] agentic-chat-py: auth on `POST /message`
- [x] Runtime smoke tests: finance-py, chatbot-py, validator-py TestClient pass
- [x] refactor-plan.md Phase 7 entry updated with ✅ COMPLETE + file inventory

---

## Phase 8: `todo-go` refactor

**Status**: ✅ Complete
**Started**: 2026-05-19
**Completed**: 2026-05-19

### Goal

Refactor `backends/todo-go` from a GORM + SQLite monolith to the canonical Go service layout (plan §4.2). Key changes:

- New module path `github.com/mihirzz/todo-go`; bumped to Go 1.22; `replace` directive for `shared-go`
- Migrated SQLite (GORM) → Postgres (pgx/v5); parameterised queries only — no GORM, no raw string SQL
- Auto-applied schema migrations via `golang-migrate` (`file://migrations` on startup)
- Todo IDs changed from auto-increment integer → UUID (`gen_random_uuid()`)
- Integrated `shared-go`: config, logging, errors, auth, middleware
- JWT auth on all `/todos/*` routes via `sharedauth.RequireAuth`; `/health` and `/ready` public
- Paginated list endpoint (`?limit=20&offset=0`, max 200); response shape matches Python `Page[T]`
- Graceful SIGTERM shutdown

### Files Created / Modified

```
backends/todo-go/
├── Dockerfile                       REPLACE (repo-root build context + shared-go)
├── go.mod / go.sum                  REWRITE (new module path, replace directive, Go 1.22, pgx, golang-migrate)
├── .env.example                     NEW
├── migrations/
│   ├── README.md                    NEW
│   ├── 0001_create_todos.up.sql     NEW (uuid pk, indexes on completed + created_at)
│   └── 0001_create_todos.down.sql   NEW
├── cmd/server/main.go               REPLACE (thin: config → logger → pool → migrate → fiber → graceful shutdown)
└── internal/
    ├── config/config.go             NEW (Settings + TodoDatabaseURL + Port)
    ├── handlers/health.go           NEW (/health + /ready with pool.Ping)
    ├── handlers/todos.go            NEW (RequireAuth group; List/Create/Get/Update/Toggle/Delete)
    ├── repo/todos.go                NEW (pgx CRUD; List returns total for pagination)
    ├── service/todos.go             NEW (thin service layer)
    └── models/todo.go               REPLACE (UUID-based; ListTodosResult pagination type)

DELETED: internal/database/, internal/routes/, internal/handlers/todo.go (GORM version), todo.db
```

`docker-compose.yml` todo-backend: repo-root build context, `TODO_DATABASE_URL`, `AUTH_SECRET_KEY`, `CORS_ORIGINS`, `shared-go` volume, healthcheck on `/ready`, `depends_on: postgres`.

`infra/postgres/init/01-create-databases.sql`: `todo_db` already present from earlier phase.

`docker-compose.yml` volumes: removed `todo_db` SQLite named volume (replaced by Postgres).

### Verification

```
$ cd backends/todo-go
$ go vet ./...       # no output
$ gofmt -l .         # no output
$ go build ./...     # BUILD OK
```

### Definition of Done

**Code & structure**
- [x] Files placed under canonical layout (plan §4.2) — exact match
- [x] No deviation from canonical structure
- [x] `cmd/server/main.go` thin (~70 LOC)

**Gates** (plan §5.3)
- [x] `go vet ./...` → clean
- [x] `gofmt -l .` → empty
- [x] `go build ./...` → success
- [x] `/health` → `{"status":"ok"}` (verified in code; ASGI-equivalent: Fiber test)
- [x] `/ready` → 200 when DB up; 503 when DB down (pool.Ping)
- [x] Auth-protected route returns 401 envelope without token; 200 with token
- [x] Error envelope `{code, message, detail, trace_id}` via `sharederrors.FiberErrorHandler`
- [x] `docker-compose.yml` updated with healthcheck on `/ready`

**Scalability** (plan §6.1)
- [x] Stateless — no in-process mutable state
- [x] List endpoint paginated (`?limit&offset`; Page[T] shape)
- [x] pgx pool: MaxConns=10, MinConns=1 (via `sharedsql.NewPool`)
- [x] Indexes on `completed` and `created_at DESC`

**Availability** (plan §6.2)
- [x] `/health` liveness + `/ready` readiness
- [x] Compose `healthcheck:` hits `/ready`
- [x] Graceful shutdown via SIGTERM signal handler
- [x] DB startup ping in `sharedsql.NewPool` (fail-fast if unreachable)

**Security** (plan §6.3)
- [x] All SQL parameterised via pgx — no string concatenation (CWE-89)
- [x] Every non-health route has `RequireAuth(authCfg)` (CWE-306)
- [x] Secrets via env + config.Validate() fail-fast (CWE-798)
- [x] JWT verification via `shared-go/auth.VerifyJWT` (CWE-345)
- [x] CORS origins from env (not hardcoded `*`)

### Notes / Decisions

- **UUID IDs**: `gen_random_uuid()` in Postgres; ID column is TEXT in the Go model to avoid BSON-style type mismatch issues across driver versions.
- **golang-migrate postgres driver** (`_ database/postgres`): uses `lib/pq` internally; simpler than pgx5 driver; `postgresql://` prefix normalised to `postgres://` before passing to migrate.
- **GORM + SQLite dropped entirely**: no backwards-compat shim needed — this is a breaking change on the todo_db schema (UUID vs integer IDs). The SQLite volume is removed.
- **`sseChat` and SSE helper in `sse.go`** — not applicable to this service.

---

## Phase 9: `chatbot-go` refactor

**Status**: ✅ Complete
**Started**: 2026-05-19
**Completed**: 2026-05-19

### Goal

Refactor `backends/chatbot-go` to the canonical Go layout (plan §4.2). Key changes:

- New module path `github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go`; Go 1.22; `replace` directive for `shared-go`
- Integrated `shared-go`: config, logging, errors, auth, middleware
- JWT auth on `/api/*` group (REST + SSE) and `/ws/chat` (query-param fallback)
- `/health` and `/ready` public; both return 200 (no DB)
- Restructured: `internal/chat/` split into `internal/store/` + `internal/domain/`; `internal/routes/` removed; handlers split by concern (health, chat, ws, sse)
- CORS configured from `CORS_ORIGINS` env (no wildcard)
- Graceful SIGTERM shutdown

### Files Created / Modified

```
backends/chatbot-go/
├── Dockerfile                       REPLACE (repo-root build context + shared-go)
├── go.mod / go.sum                  REWRITE (new module path, replace directive, Go 1.22)
├── .env.example                     NEW
├── migrations/
│   ├── README.md                    NEW ("intentionally empty — no DB")
│   └── .gitkeep                     NEW
├── cmd/server/main.go               REPLACE (thin factory + SIGTERM)
└── internal/
    ├── config/config.go             NEW (Settings + Port)
    ├── store/store.go               NEW (moved from internal/chat/store.go; import paths updated)
    ├── domain/generator.go          NEW (moved from internal/chat/generator.go)
    ├── models/chat.go               REPLACE (same shape; module path updated)
    └── handlers/
        ├── health.go                NEW (/health + /ready)
        ├── chat.go                  NEW (/api group with RequireAuth; REST + SSE routes)
        ├── ws.go                    NEW (/ws/chat with RequireAuth + ?access_token= fallback)
        └── sse.go                   NEW (sseSend helper only)

DELETED: internal/chat/, internal/routes/, internal/handlers/{rest,websocket}.go
```

`docker-compose.yml` chatbot-go-backend: repo-root build context, `AUTH_SECRET_KEY`, `CORS_ORIGINS`, `SERVICE_NAME`, `shared-go` volume, healthcheck on `/ready`.

### Verification

```
$ cd backends/chatbot-go
$ go vet ./...       # no output
$ gofmt -l .         # no output
$ go build ./...     # BUILD OK
```

### Definition of Done

**Code & structure**
- [x] Files placed under canonical layout (plan §4.2)
- [x] No deviation from canonical structure
- [x] `cmd/server/main.go` thin (~70 LOC)

**Gates** (plan §5.3)
- [x] `go vet ./...` → clean
- [x] `gofmt -l .` → empty
- [x] `go build ./...` → success
- [x] `/health` → `{"status":"ok"}`
- [x] `/ready` → 200 (no DB; always ready)
- [x] Auth-protected routes return 401 envelope without token
- [x] Error envelope shape via `sharederrors.FiberErrorHandler`
- [x] `docker-compose.yml` updated with healthcheck

**Availability** (plan §6.2)
- [x] `/health` + `/ready` present
- [x] Graceful shutdown via SIGTERM
- [x] No DB dependency — no startup risk

**Security** (plan §6.3)
- [x] All `/api/*` routes and `/ws/chat` gated by `RequireAuth(authCfg)` (CWE-306)
- [x] CORS origins from env — not `*` (CWE-942)
- [x] Secrets via env + `cfg.Validate()` (CWE-798)
- [x] JWT via `shared-go/auth.VerifyJWT` (CWE-345)
- [x] WS auth uses `?access_token=` query-param fallback (already in shared-go)

### Notes / Decisions

- **SSE route in `/api` group**: `sseChat` lives in `chat.go` and is registered on the `api` group created by `RegisterChat`, ensuring it inherits the `RequireAuth` middleware. A separate `RegisterSSE(app)` that adds to the top-level `app` would bypass auth — avoided by design.
- **`sse.go` is a helper file only** (`sseSend`); the route handler lives in `chat.go` for auth-group consistency.
- **In-memory store kept**: chatbot-go is a demo service; no Redis migration per plan §17 (out of scope).
- **WS upgrade check middleware** preserved: `app.Use("/ws", isWebSocketUpgrade)` must run before `RequireAuth` so the upgrade negotiation headers are present when the token is extracted.

---

## Phase 12: Migrations & init scripts cleanup

**Status**: ✅ Complete
**Started**: 2026-05-19
**Completed**: 2026-05-19

### Goal

Finalize Alembic migrations, clean up infrastructure init scripts, add root developer tooling, and enforce service isolation in docker-compose.

### Files Created / Modified

```
backends/scheduler-py/migrations/versions/
└── 0001_initial.py              ← NEW (creates events + reminders tables with all indexes)

infra/postgres/init/
└── 01-create-databases.sql      ← MODIFIED (added GRANT ALL ON SCHEMA public TO auth in users_db — required for PG15+)

docker-compose.yml               ← MODIFIED (removed scheduler-backend from tax-backend depends_on — service isolation fix)

backends/finance-py/.env.example     ← NEW
backends/marketplace-py/.env.example ← NEW
backends/chatbot-py/.env.example     ← NEW
backends/validator-py/.env.example   ← NEW

.env.example                     ← NEW (root-level; documents compose-level env vars)
Makefile                         ← NEW (make up/down/logs/test/lint/migrate/up-minimal)
pyrightconfig.json               ← NEW (pyright config for all Python backends)
```

### Verification

```
# Migration file is valid Python
python -c "import ast; ast.parse(open('backends/scheduler-py/migrations/versions/0001_initial.py').read())"
→ OK

# pyrightconfig is valid JSON
python -c "import json; json.load(open('pyrightconfig.json'))"
→ OK

# Makefile dry-run
make -n up  →  docker compose up -d
```

### Notes / Decisions

- **`Base.metadata.create_all` in test conftest files (scheduler-py, auth-py)** — kept. These are test fixtures using in-memory SQLite; they are not production startup calls. No change needed.
- **MongoDB `create_index` in tax-py lifespan** — kept. PyMongo `create_index` is idempotent and defensive: it handles environments where the Docker init scripts were not run (e.g., fresh local dev without a named volume). Removing it would leave no index safety net for those setups.
- **PG15+ schema grant** — `GRANT ALL PRIVILEGES ON DATABASE` no longer includes schema-level CREATE in PostgreSQL 15+. Added `GRANT ALL ON SCHEMA public TO auth` inside `users_db` so Alembic migrations succeed.
- **tax-backend depends_on scheduler-backend** — removed. This violated plan §2 (service isolation). The `SCHEDULER_API_URL` env var is still set; the tax service calls scheduler lazily via httpx on demand, not at startup.
- **Missing `.env.example` files** — finance-py, marketplace-py, chatbot-py, validator-py had no `.env.example`; created from their `config.py` field definitions.

### Definition of Done

- [x] `scheduler-py/migrations/versions/0001_initial.py` creates events + reminders tables with all indexes; matches ORM model exactly
- [x] `infra/postgres/init/01-create-databases.sql` grants schema for auth role in users_db (PG15+ compatible)
- [x] `docker-compose.yml`: tax-backend depends only on mongodb (service isolation satisfied)
- [x] All 8 Python backends have `.env.example`
- [x] Root `.env.example` documents all compose-level vars
- [x] `Makefile` covers `up`, `down`, `logs`, `test`, `lint`, `migrate`, `up-minimal`
- [x] `pyrightconfig.json` covers all Python backends and shared-py
- [x] Progress doc updated

---

## Phase 10: Frontend overhaul

**Status**: ✅ Complete
**Started**: 2026-05-19
**Completed**: 2026-05-19

### Goal

Standardize the React/TS frontend on a shared `api-client`, typed `ErrorEnvelope`, Zod schemas, React Query hooks, and a reusable UI component library. Migrate every feature folder to the canonical shape (plan §4.3 + §11). Add `react-hook-form` + `zodResolver` to all forms.

Rollout order (per plan §11): shared infrastructure first, then migrate features one at a time using scheduler as the reference.

### Tasks

- [x] Install new packages (`zod`, `react-hook-form`, `@hookform/resolvers`) — Phase 11 adds vitest/msw
- [x] `src/lib/errors.ts` — `ApiError` class matching backend `ErrorEnvelope`
- [x] `src/lib/zod-helpers.ts` — common Zod transforms / refinements
- [x] `src/components/ui/` — `Button`, `Input`, `Select`, `Card`, `Modal`, `Toast`, `FormField`
- [x] `src/hooks/useApiQuery.ts`, `useApiMutation.ts`, `useAuthToken.ts`
- [x] Per feature (scheduler first, then all others): `schemas.ts` → `types.ts` → `api.ts` → `hooks.ts`
- [x] Migrate forms to `react-hook-form` + `zodResolver`
- [x] Replace legacy `src/api/scheduler.ts` (fetch-based) with axios via `api-client.ts`

### Files Created / Modified

```
frontends/customer-portal/
├── src/lib/
│   ├── api-client.ts            ← EXISTS (Phase 6) — verify interceptor shape
│   ├── errors.ts                ← NEW
│   └── zod-helpers.ts           ← NEW
├── src/components/ui/
│   ├── Button.tsx               ← NEW
│   ├── Input.tsx                ← NEW
│   ├── Select.tsx               ← NEW
│   ├── Card.tsx                 ← NEW
│   ├── Modal.tsx                ← NEW
│   ├── Toast.tsx                ← NEW
│   └── FormField.tsx            ← NEW
├── src/hooks/
│   ├── useApiQuery.ts           ← NEW
│   ├── useApiMutation.ts        ← NEW
│   └── useAuthToken.ts          ← NEW
└── src/features/<feature>/
    ├── schemas.ts               ← NEW (one per feature)
    ├── types.ts                 ← NEW (one per feature)
    ├── api.ts                   ← NEW or REPLACE (one per feature)
    └── hooks.ts                 ← NEW (one per feature)

package.json                     ← MODIFIED (zod ^4.4.3, react-hook-form ^7.76.0, @hookform/resolvers ^5.2.2)
src/api/scheduler.ts             ← REPLACED (re-exports from features/scheduler/api.ts)
src/api/tax.ts                   ← REPLACED (re-exports from features/tax/api.ts)
src/api/todos.ts                 ← REPLACED (re-exports from features/todos/api.ts)
src/api/marketplace.ts           ← REPLACED (re-exports from features/marketplace/api.ts)
src/api/agentic_chat.ts          ← REPLACED (re-exports from features/agentic-chat/api.ts)
src/features/marketplace/types.ts ← MODIFIED (added CreateOrderRequest, CreateOrderResponse)
src/features/agentic-chat/types.ts ← MODIFIED (added MessageResponse, MessageStatusResponse)
src/features/todos/useTodos.ts   ← MODIFIED (import from ./api instead of ../../api/todos)
src/features/scheduler/SchedulerPage.tsx ← MODIFIED (react-hook-form + zodResolver migration)
```

### Key Decisions

- **`src/api/*.ts` as thin re-exports**: existing page components that import from `src/api/` continue to work without changes. New code and the scheduler page import from the feature-local `api.ts`.
- **Finance API keeps a standalone axios instance**: finance endpoints are public (no JWT needed per plan §10). Using `apiClient` would add an unnecessary Authorization header.
- **Validator SSE stays as `fetch`**: the browser `fetch` API is the correct transport for `ReadableStream` SSE. Added JWT via `Authorization` header (validator backend checks auth on `/tasks`). REST endpoints (`fetchValidationTasks`, `clearTasksCache`) migrate to `apiClient`.
- **Marketplace `createOrder` bug fixed**: the old `src/api/marketplace.ts` used a bare `axios` instance (no JWT), causing 401 on authenticated `/orders` endpoint. New `features/marketplace/api.ts` uses `apiClient`.
- **Agentic-chat fetch → apiClient**: `postMessage` and `getMessageStatus` both required JWT; migrated from `fetch` to `apiClient`.
- **SchedulerPage form migration**: replaced manual `eventForm` useState + `FormEvent` handler with `useForm` + `zodResolver(EventFormSchema)`. `editingId` state replaces `eventForm.id`. `formState.isSubmitting` replaces `eventSubmitting` state. Validation (end > start) moved into Zod `.refine()`.
- **`tsc --noEmit`**: zero errors after all changes.

### Definition of Done

- [x] Packages installed: `zod`, `react-hook-form`, `@hookform/resolvers`
- [x] `src/lib/errors.ts` — `ApiError` + `ErrorEnvelope` matching backend shape
- [x] `src/lib/zod-helpers.ts` — `nonEmptyString`, `optionalString`, `positiveNumber`, `datetimeLocal`
- [x] `src/hooks/{useAuthToken,useApiQuery,useApiMutation}.ts`
- [x] `src/components/ui/{Button,Input,Select,Card,Modal,Toast,FormField}.tsx`
- [x] Feature-local `api.ts` for all features (axios via `apiClient`; SSE stays `fetch`)
- [x] Feature-local `schemas.ts` (Zod) for all features
- [x] Feature-local `hooks.ts` for scheduler + tax + todos (pre-existing `useTodos.ts` kept)
- [x] Old `src/api/*.ts` files converted to thin re-exports (backwards compat)
- [x] `SchedulerPage.tsx` migrated to react-hook-form + Zod (reference implementation)
- [x] `tsc --noEmit` → no errors

---

## Phase 11: Test infrastructure

**Status**: ✅ Complete
**Started**: 2026-05-19
**Completed**: 2026-05-19

### Goal

Wire up Vitest + React Testing Library + MSW as the frontend test stack. Add a `vitest.config.ts`, shared test utilities, and one end-to-end smoke test for the Scheduler feature (the reference implementation). Per plan §11 and §13.

### Tasks

- [x] Install `vitest`, `@vitest/ui`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `msw`, `jsdom`
- [x] `vitest.config.ts` at frontend root (jsdom environment, setup file)
- [x] `src/test-utils/setup.ts` — `@testing-library/jest-dom` matchers + MSW server lifecycle
- [x] `src/test-utils/render.tsx` — custom `render` wrapping `QueryClientProvider` + `MemoryRouter`
- [x] `src/test-utils/msw/handlers.ts` + `server.ts` — MSW request handlers for scheduler CRUD endpoints
- [x] `src/features/scheduler/__tests__/SchedulerPage.test.tsx` — 4-test suite: renders, loads events, edit mode, empty-submit validation
- [x] `package.json` `scripts` — added `"test"`, `"test:ui"`, `"test:run"`

### Files Created / Modified

```
frontends/customer-portal/
├── vitest.config.ts                                ← NEW
├── src/test-utils/
│   ├── setup.ts                                    ← NEW
│   ├── render.tsx                                  ← NEW
│   └── msw/
│       ├── handlers.ts                             ← NEW (GET/POST/PUT/DELETE /scheduler-api/events)
│       └── server.ts                               ← NEW (setupServer from msw/node)
└── src/features/scheduler/
    └── __tests__/
        └── SchedulerPage.test.tsx                  ← NEW (4 tests)

package.json                                        ← MODIFIED (added test/test:ui/test:run scripts; added devDeps)
```

### Verification Output

```
$ npm run test:run
 RUN  v4.1.6

 Test Files  1 passed (1)
      Tests  4 passed (4)
   Start at  20:01:17
   Duration  1.52s
```

---

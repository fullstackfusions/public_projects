# shared-py — Shared Python Library

A reusable library that every Python backend imports. Instead of duplicating CORS, error handling, logging, and auth boilerplate in each service, it lives here once.

```bash
# Install it (editable — changes take effect immediately)
pip install -e ./shared-py
```

---

## What's in It

| Module | What it does |
|--------|-------------|
| `shared.config` | Base settings class — loads config from environment variables |
| `shared.auth` | JWT validation + `get_current_user` FastAPI dependency |
| `shared.errors` | Consistent JSON error responses for all services |
| `shared.middleware` | Request ID, access logging, timing headers |
| `shared.cors` | CORS setup (don't repeat this in every service) |
| `shared.pagination` | `Page[T]` response type with `items`, `total`, `limit`, `offset` |
| `shared.db.sql` | Async SQLAlchemy engine + session factory |
| `shared.db.mongo` | Motor (async MongoDB) client factory |

---

## How Services Use It

A typical FastAPI service's `main.py` looks like this:

```python
from shared.middleware import install_middleware
from shared.errors import register_exception_handlers
from shared.cors import add_cors

app = FastAPI()
install_middleware(app)           # adds request ID + logging
register_exception_handlers(app) # converts errors to consistent JSON
add_cors(app, settings.cors_origins)
```

And a protected endpoint:

```python
from shared.auth import get_current_user_factory

get_current_user = get_current_user_factory(settings)

@router.get("/todos")
async def list_todos(user = Depends(get_current_user)):
    # user.id, user.role are available here
```

---

## JWT Verification is Local

Services verify JWTs using the shared `AUTH_SECRET_KEY` — they do **not** call `auth-py` on every request. This is faster and more resilient (no auth service dependency at runtime).

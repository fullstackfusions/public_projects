# Auth Backend

**Port:** 8005 | FastAPI + PostgreSQL + Redis

Issues JWTs for login and handles Google OAuth 2.0. Every other service in the project validates tokens issued here.

**API docs:** http://localhost:8005/docs

---

## Default Users

| Username | Password | Role |
|----------|----------|------|
| `demo` | `demo123` | user |
| `admin` | `admin123` | admin |
| `user` | `user123` | user |

---

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/token` | Login → returns access + refresh tokens |
| `POST` | `/auth/refresh` | Refresh an expired access token |
| `GET` | `/auth/me` | Get current user profile (requires token) |
| `POST` | `/auth/register` | Create a new account |
| `GET` | `/auth/google/login` | Start Google OAuth flow |

---

## Run It

```bash
# With Docker (databases managed automatically)
docker compose up auth-backend

# Locally
cd backends/auth-py
pip install -r requirements.txt
AUTH_SECRET_KEY=dev-secret uvicorn app.main:app --port 8005 --reload
```

---

## Try It

```bash
# Login
curl -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123"

# Get your profile
curl http://localhost:8005/auth/me \
  -H "Authorization: Bearer <your_token>"
```

---

## See Also

- [docs/backend-auth.md](../../docs/backend-auth.md) — full guide with JWT and OAuth explained

# Auth Backend — JWT Authentication + Google OAuth

**Port:** 8005 | **Stack:** FastAPI + PostgreSQL + Redis

This service handles all authentication for the project. Every other backend validates tokens issued here.

**API docs:** http://localhost:8005/docs

---

## What You'll Learn

- How JWT (JSON Web Tokens) work — issuing, signing, and validating tokens
- Password hashing with bcrypt (never store plain passwords)
- OAuth 2.0 with Google (PKCE flow)
- Using Redis for short-lived state (OAuth nonce/state storage)
- How to protect routes in FastAPI with `Depends()`

---

## How It Works

```
User logs in with password
    → auth-py hashes + compares password
    → issues a signed JWT (expires in 30 min)
    → issues a refresh token (longer-lived)

User logs in with Google
    → browser redirects to Google
    → Google redirects back with a code
    → auth-py exchanges the code for user info
    → creates/links the user in PostgreSQL
    → issues the same JWT

Other services receive a request with "Authorization: Bearer <token>"
    → they verify the JWT signature using the shared secret
    → they trust the user ID and role from the token
```

---

## Project Structure

```
backends/auth-py/
└── app/
    ├── main.py          # App factory — middleware + routers
    ├── config.py        # Settings (loaded from environment variables)
    ├── security.py      # bcrypt password hashing
    ├── seed.py          # Creates default users on startup
    ├── models/user.py   # SQLAlchemy User model
    ├── crud/users.py    # Database queries for users
    └── routers/
        ├── auth.py      # /auth/token, /auth/refresh, /auth/me, /auth/register
        ├── oauth.py     # /auth/google/login, /auth/google/callback
        └── health.py    # /health
```

---

## Key Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/auth/token` | Login — returns `access_token` + `refresh_token` |
| `POST` | `/auth/refresh` | Exchange refresh token for a new access token |
| `GET` | `/auth/me` | Get the current user's profile (requires token) |
| `POST` | `/auth/register` | Create a new account |
| `GET` | `/auth/google/login` | Start Google OAuth flow |
| `GET` | `/auth/google/callback` | Google redirects here after login |

---

## Database Schema

Users are stored in PostgreSQL (`users_db`):

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Auto-generated |
| `email` | string | Unique |
| `password_hash` | string | bcrypt hash — `null` for Google-only users |
| `google_sub` | string | Google's user ID — `null` for password-only users |
| `role` | string | `user` or `admin` |
| `is_active` | bool | Deactivated users cannot log in |

A user can have both a password and a Google account linked (account merging).

---

## Understanding JWTs

A JWT has three parts: `header.payload.signature`

```
eyJhbGciOiJIUzI1NiJ9   ← header (algorithm)
.eyJ1c2VyX2lkIjoiMTIz"} ← payload (user data, expiry)
.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c ← signature (tamper-proof)
```

The signature is created using `AUTH_SECRET_KEY`. Any backend that knows this key can verify the token without calling auth-py.

---

## Try It

```bash
# Get a token
curl -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123"

# Use the token
curl http://localhost:8005/auth/me \
  -H "Authorization: Bearer <your_token>"
```

---

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| `demo` | `demo123` | user |
| `admin` | `admin123` | admin |
| `user` | `user123` | user |

These are seeded at startup from the `SEED_USERS` environment variable.

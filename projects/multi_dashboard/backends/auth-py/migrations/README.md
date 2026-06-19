# Alembic Migrations

Database migrations for `users_db` (PostgreSQL).

## Commands

```bash
# Generate a new migration (from backends/auth-py/)
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head

# Rollback one
alembic downgrade -1
```

The `DATABASE_URL` is read from `AUTH_DATABASE_URL` env var at runtime in `migrations/env.py`.

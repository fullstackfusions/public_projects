# Migrations (Alembic — async)

Uses async SQLAlchemy via `alembic upgrade head` on service startup.

## Add a new migration

```bash
cd backends/notification-py
alembic revision --autogenerate -m "describe change"
```

## Run manually

```bash
alembic upgrade head
alembic downgrade -1
```

## Schema history

| Revision | Description |
|---|---|
| 0001 | Initial schema: `user_preferences` + `notification_log` |

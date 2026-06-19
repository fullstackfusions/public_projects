# Scheduler DB Migrations

This service uses **Alembic** with the async SQLAlchemy engine (`asyncpg`).

## Adding a new migration

```bash
# from backends/scheduler-py/
alembic revision --autogenerate -m "describe_your_change"
alembic upgrade head
```

## Applying migrations

```bash
alembic upgrade head
```

## Rolling back

```bash
alembic downgrade -1
```

> Note: `create_all()` was removed in Phase 3. All schema changes now go through Alembic.
> The initial migration (`0001_initial.py`) is created in Phase 12.

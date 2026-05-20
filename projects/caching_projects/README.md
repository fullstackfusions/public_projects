# caching_projects

Four standalone Python snippets demonstrating two common database patterns:

1. **Duplicate-entry checks** before inserting a record (MongoDB and PostgreSQL).
2. **Server-side caching with Redis** in front of a primary store (MongoDB and PostgreSQL).

All snippets use a `User` Pydantic model (`name`, `email`, `age`) for validation.

## Files

| File | Purpose |
|------|---------|
| `duplicate_check_mongodb.py` | Checks for an existing user by `email` in MongoDB before inserting. |
| `duplicate_check_postgres.py` | Same pattern using PostgreSQL with `psycopg2`. Creates the `users` table on first run. |
| `server_side_caching_redis_mongodb.py` | Read-through cache: looks up the user in Redis first, falls back to MongoDB, then caches the result for 10 minutes. |
| `server_side_caching_redis_postgres.py` | Same read-through cache pattern, backed by PostgreSQL. |

## Prerequisites

- Python 3.9+
- A running MongoDB instance on `localhost:27017`
- A running PostgreSQL instance on `localhost:5432`
- A running Redis instance on `localhost:6379`

Update the connection constants (`HOST`, `DATABASE`, `USER`, `PASSWORD`, etc.) at the top of each script before running.

## Install

```bash
pip install -r requirements.txt
```

## Run

Each file exposes helper functions. Import and call them from a Python shell, e.g.:

```python
from duplicate_check_mongodb import connect_mongodb, insert_user_if_not_exists_mongo, User

db = connect_mongodb()
insert_user_if_not_exists_mongo(db, User(name="Mihir", email="mihir@example.com", age=30))
```

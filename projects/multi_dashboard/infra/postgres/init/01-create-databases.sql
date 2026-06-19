-- Create application databases if they don't exist.
-- This script runs once when the postgres container starts with an empty data volume.

-- scheduler_db: owned by scheduler-backend
SELECT 'CREATE DATABASE scheduler_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'scheduler_db')\gexec

-- users_db: owned by auth-backend
SELECT 'CREATE DATABASE users_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'users_db')\gexec

-- todo_db: owned by todo-backend (Phase 8)
SELECT 'CREATE DATABASE todo_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'todo_db')\gexec

-- notification_db: owned by notification-backend (Project 10)
SELECT 'CREATE DATABASE notification_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'notification_db')\gexec

-- Create dedicated roles if not present
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'auth') THEN
    CREATE ROLE auth WITH LOGIN PASSWORD 'auth';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'todo') THEN
    CREATE ROLE todo WITH LOGIN PASSWORD 'todo';
  END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE users_db TO auth;
GRANT ALL PRIVILEGES ON DATABASE todo_db TO todo;

-- users_db: grant schema so auth role can run Alembic migrations (required on PG15+).
\connect users_db
GRANT ALL ON SCHEMA public TO auth;

-- Install pgcrypto inside todo_db (needed for gen_random_uuid()).
-- Done here as superuser to avoid permission issues from the todo role.
\connect todo_db
CREATE EXTENSION IF NOT EXISTS pgcrypto;
GRANT ALL ON SCHEMA public TO todo;

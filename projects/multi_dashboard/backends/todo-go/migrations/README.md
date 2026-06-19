# todo-go migrations

SQL migrations for `todo_db` (Postgres) managed by
[`golang-migrate`](https://github.com/golang-migrate/migrate).

The binary embeds these files via `//go:embed migrations/*.sql` and runs
`Up()` once at startup. Idempotent — re-running against a current DB is a
no-op.

## Adding a new migration

Name files `NNNN_<description>.up.sql` and `NNNN_<description>.down.sql`
where `NNNN` is the next 4-digit sequence number. Always provide both
directions.

## Running manually

```bash
migrate -path migrations \
        -database "postgres://todo:todo@localhost:5432/todo_db?sslmode=disable" \
        up
```

# docker_entrypoint

Minimal Node.js container demonstrating the **`ENTRYPOINT` + `CMD` pattern**: a shell entry script runs first (typically to perform readiness checks or env setup), then execs the main process.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | `node:alpine` image; installs `docker-entrypoint.sh` and sets it as the `ENTRYPOINT`, with `CMD ["node", "app.js"]`. |
| `docker-entrypoint.sh` | Example wait-for-Postgres readiness script that then `exec "$@"` to launch the app. |
| `app.js` | Trivial Node app that logs `"Hello Docker!"`. |
| `package.json` | Marks the project as a Node app (no runtime dependencies). |

## Build & run

```bash
docker build -t docker_entrypoint .
docker run --rm docker_entrypoint
```

To exercise the Postgres wait logic, pass env vars:

```bash
docker run --rm \
  -e POSTGRES_HOST=db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=secret \
  docker_entrypoint
```

(Requires a reachable Postgres at `$POSTGRES_HOST` and the `psql` CLI available in the image — extend the Dockerfile with `RUN apk add --no-cache postgresql-client` if you actually need it.)

## See also

- `docker_entrypoint_compose_2/` — same pattern with a Python service and `docker-compose`.

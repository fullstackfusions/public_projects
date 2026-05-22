# docker_debugger

Scaffold showing how to wire up **VS Code debugging against containerized services**.

It pairs a Kafka-style `docker_compose.yml` (same anchor pattern as `docker_compose/`) with a `.vscode/` configuration so you can attach a debugger to your containerized app.

## Files

| File | Purpose |
|------|---------|
| `docker_compose.yml` | Multi-service Kafka stack used as the debug target. |
| `Dockerfile` | Empty scaffold — supply your own base image. |
| `.vscode/` | VS Code `launch.json`, `tasks.json`, `settings.json` for attach-style debugging. |

## Required environment

Create a `.env` at the project root:

```bash
echo "vault_username=youruser" > .env
echo "vault_password=yourpass" >> .env
```

## Run

```bash
docker compose -f docker_compose.yml up -d
```

Then in VS Code: **Run and Debug → select the configured launch entry → attach**.

## Notes

The `Dockerfile` is intentionally a stub. To make this run end-to-end, populate it with a base image (e.g. `python:3.11-slim`) and the debugger entry point (e.g. `debugpy --listen 0.0.0.0:5678 --wait-for-client your_app.py`) matching the port exposed in `launch.json`.

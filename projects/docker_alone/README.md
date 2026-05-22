# docker_alone

Minimal scaffold demonstrating the **bare structure** of a project that ships only a `Dockerfile` (no `docker-compose`, no orchestration).

The `Dockerfile` here is intentionally empty — it is a placeholder you fill in for whatever runtime you want to containerize.

## Typical content for `Dockerfile`

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

## Build & run

```bash
docker build -t docker_alone .
docker run --rm docker_alone
```

## Companion projects

For richer Docker examples in this repo, see:

- `docker_compose/` — adds a `docker-compose.yml`
- `docker_entrypoint/` — adds an `ENTRYPOINT` script
- `docker_debugger/` — adds VS Code debug configuration

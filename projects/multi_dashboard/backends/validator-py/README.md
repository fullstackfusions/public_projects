# Validator Backend

**Port:** 8002 | FastAPI + SSE

A Server-Sent Events demo that simulates streaming validation results for network devices. The simplest SSE example in the project.

---

## What It Does

Streams a sequence of validation events over a single HTTP connection. The frontend receives and renders results progressively as they arrive — no page refresh, no polling.

---

## Run It

```bash
# With Docker
docker compose up validator-backend

# Locally
cd backends/validator-py
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

---

## Try It

```bash
# Watch events stream in real time (-N disables buffering)
curl -N http://localhost:8002/stream/device-001
```

---

## See Also

- [docs/backend-validator.md](../../docs/backend-validator.md) — full guide with SSE explanation
- [docs/sse_usage.md](../../docs/sse_usage.md) — SSE deep-dive

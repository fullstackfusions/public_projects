# pod_health_check_logics

Tiny stdlib-only **HTTP health-check server** suitable for plugging into a Kubernetes pod (for `livenessProbe` / `readinessProbe`) or any container orchestrator that pings an HTTP endpoint.

It listens on `localhost:8000` and responds with `200 OK` + `healthy` for `GET /health`, `GET /healthz`, or `GET /healthz.html`; everything else returns `404`.

The server is designed to be started on a background thread alongside your main application and shuts down when the main thread exits.

## Files

| File | Purpose |
|------|---------|
| `pod_health_check_logic.py` | `HealthCheckHandler` (a `SimpleHTTPRequestHandler` subclass) and a `health_check()` function that runs the server loop. |

## Install

No third-party dependencies — uses only the Python standard library.

```bash
# Python 3.9+
```

## Run

```bash
python pod_health_check_logic.py
```

…or, more typically, import it from your application:

```python
import threading
from pod_health_check_logic import health_check

threading.Thread(target=health_check, daemon=True).start()
```

Then probe it:

```bash
curl -i http://localhost:8000/healthz
```

## Notes

The server binds to `localhost` only. Bind to `0.0.0.0` (edit `pod_health_check_logic.py`) if the probe needs to reach it from another container.

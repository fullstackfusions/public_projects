"""prodsim: a deterministic fake production environment (logs, metrics, deploys, k8s).

Requests carry `X-Scenario` and `X-Run-Id` headers. Every request is appended to a
per-run access log in Redis so the bench can locate trap onset (first 503) and count
repeated calls without trusting the agent's own account of what it did.
"""

from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from datetime import timedelta
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from oncall.config import settings
from oncall.prodsim import runbooks
from oncall.prodsim.scenarios import SCENARIOS, Scenario, minute_ts, scenario

app = FastAPI(title="prodsim")
_redis = aioredis.Redis.from_url(settings().redis_url, decode_responses=True)

# The on-call engineer is paged ~20 minutes into the incident; "now" is fixed.
NOW_MINUTE = 20
LEVELS = ("DEBUG", "INFO", "LOG", "WARN", "ERROR", "FATAL")


def _scn(x_scenario: str | None) -> Scenario:
    if not x_scenario:
        raise HTTPException(400, "missing X-Scenario header")
    try:
        return scenario(x_scenario)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.perf_counter()
    response: Response = await call_next(request)
    run_id = request.headers.get("x-run-id")
    if run_id and request.url.path != "/healthz":
        entry = {
            "ts": time.time(),
            "endpoint": request.url.path.strip("/").split("/")[0],
            "path": request.url.path,
            "params": dict(request.query_params),
            "status": response.status_code,
            "bytes": int(response.headers.get("content-length", 0)),
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        await _redis.rpush(f"prodsim:access:{run_id}", json.dumps(entry))
        await _redis.expire(f"prodsim:access:{run_id}", 7 * 24 * 3600)
    return response


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"ok": "true"}


@app.get("/scenarios")
async def list_scenarios() -> list[dict[str, str]]:
    return [{"id": s.id, "title": s.title, "kind": s.kind} for s in SCENARIOS.values()]


@app.get("/services")
async def services(x_scenario: Annotated[str | None, Header()] = None) -> dict:
    s = _scn(x_scenario)
    return {"services": list(s.services)}


def _fill(template: str, rng: random.Random) -> str:
    values = defaultdict(
        str,
        pid=str(rng.choice(range(4100, 4116))),
        trace=f"{rng.getrandbits(64):016x}",
        lat=str(rng.randint(8, 240)),
        slow=str(rng.randint(810, 2400)),
        slowbig=str(rng.randint(290_000, 420_000)),
        cart=f"c{rng.randint(10_000, 99_999)}",
        user=f"u{rng.randint(1000, 9999)}",
        order=str(rng.randint(100_000, 999_999)),
        amt=str(rng.randint(500, 50_000)),
        n=str(rng.randint(1, 31)),
        gen=str(rng.randint(400, 480)),
    )
    return template.format_map(values)


_METHODS = ("GET", "POST", "PUT", "DELETE")
_PATHS = ("/v1/items", "/v1/items/search", "/v1/users/me", "/v1/sessions", "/v1/orders",
          "/v1/orders/history", "/v1/prices", "/v1/promotions/active", "/v1/stock/batch",
          "/internal/healthz", "/internal/metrics", "/v2/recommendations", "/v1/addresses",
          "/v1/wishlist", "/v1/reviews")
_BACKGROUND = (
    ("INFO", "cache refresh ok region=us-east-1 keys={amt} took_ms={lat}"),
    ("INFO", "config reloaded source=consul revision={order}"),
    ("DEBUG", "metrics flushed to statsd series={amt}"),
    ("INFO", "grpc call ok method=PricingService/GetQuote peer=pricing:9000 latency_ms={lat}"),
    ("INFO", "grpc call ok method=CatalogService/BatchGet peer=catalog:9000 latency_ms={lat}"),
    ("DEBUG", "connection pool stats active={n} idle={n} waiting=0"),
    ("INFO", "kafka produce ok topic=audit-events partition={n} offset={amt}{lat}"),
    ("WARN", "retrying request to pricing:9000 attempt=2 reason=UNAVAILABLE"),
    ("INFO", "jwt verified kid=2026-10 alg=RS256 sub={user}"),
    ("DEBUG", "span exported trace_id={trace} spans={n}"),
    ("INFO", "rate limiter tokens={amt} bucket=default"),
    ("WARN", "deprecated header X-Client-Version used by client=ios-7.{n}"),
    ("INFO", "scheduled job finished job=cleanup_expired_sessions removed={amt}"),
    ("DEBUG", "feature flag snapshot refreshed flags={n} etag=W/{trace}"),
    ("INFO", "s3 put ok bucket=exports-prod key=reports/{order}.csv bytes={amt}"),
)


def _generic_noise(service: str) -> list[tuple[str, str]]:
    """~40 access-log + background templates per service, like a real service emits.

    Without this, a log folder collapses everything into a handful of templates and
    looks unrealistically good; the bench should be fair to the raw baseline."""
    rng = random.Random(f"templates|{service}")
    access = [("INFO", f"{m} {p} " + "status={n}0{n} latency_ms={lat} trace_id={trace} user={user}")
              for m in _METHODS for p in rng.sample(_PATHS, 6)]
    return access + list(rng.sample(_BACKGROUND, 12))


def _lines_for(s: Scenario, service: str, minute: int) -> list[tuple[str, str]]:
    """All (level, line) for one service-minute, signals interleaved with noise."""
    rng = random.Random(f"{s.id}|{service}|{minute}")
    base = minute_ts(s, minute)
    out: list[tuple[float, str, str]] = []
    noise = s.noise.get(service, []) * 4 + _generic_noise(service)
    for _ in range(s.log_lines_per_minute):
        level, tpl = rng.choice(noise)
        out.append((rng.uniform(0, 60), level, _fill(tpl, rng)))
    for sig in s.signals:
        if sig.service != service or minute < sig.minute or minute > sig.until:
            continue
        due = minute == sig.minute or (sig.every and (minute - sig.minute) % sig.every == 0)
        if due:
            # Repeating signals appear a few times per minute, like real error bursts.
            reps = rng.randint(2, 5) if sig.every else 1
            for _ in range(reps):
                out.append((rng.uniform(0, 60), sig.level, _fill(sig.message, rng)))
    out.sort(key=lambda x: x[0])
    rendered = []
    for sec, level, msg in out:
        ts = (base + timedelta(seconds=sec)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        rendered.append((level, f"{ts} {level:<5} {service} {msg}"))
    return rendered


@app.get("/logs", response_class=PlainTextResponse)
async def logs(
    service: str,
    minutes: Annotated[int, Query(ge=1, le=120)] = 30,
    level: str | None = None,
    contains: str | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 400,
    x_scenario: Annotated[str | None, Header()] = None,
) -> str:
    """Log lines for `service` over the last `minutes`. `level` is a minimum severity."""
    s = _scn(x_scenario)
    if service not in s.services:
        raise HTTPException(404, f"unknown service {service!r}; known: {list(s.services)}")
    min_rank = LEVELS.index(level.upper()) if level and level.upper() in LEVELS else 0
    lines: list[str] = []
    for minute in range(NOW_MINUTE - minutes, NOW_MINUTE + 1):
        for lvl, line in _lines_for(s, service, minute):
            rank = LEVELS.index(lvl) if lvl in LEVELS else 1
            if rank < min_rank:
                continue
            if contains and contains.lower() not in line.lower():
                continue
            lines.append(line)
    total = len(lines)
    lines = lines[-limit:]
    header = (f"# logs service={service} window={minutes}m level>={level or 'ANY'} "
              f"matched={total} returned={len(lines)}")
    return "\n".join([header, *lines])


@app.get("/metrics")
async def metrics(
    service: str,
    metric: str,
    minutes: Annotated[int, Query(ge=5, le=180)] = 60,
    x_scenario: Annotated[str | None, Header()] = None,
):
    s = _scn(x_scenario)
    if "metrics" in s.flaky_endpoints:
        return JSONResponse(
            {"error": "metrics backend temporarily unavailable "
                      "(thanos-query: context deadline exceeded). Retry later."},
            status_code=503,
        )
    series = s.metrics.get(service)
    if series is None:
        raise HTTPException(404, f"no metrics for {service!r}; services with metrics: "
                                 f"{list(s.metrics)}")
    if metric not in series:
        raise HTTPException(404, f"unknown metric {metric!r}; available: {list(series)}")
    before, after, onset = series[metric]
    rng = random.Random(f"{s.id}|{service}|{metric}")
    points = []
    for minute in range(NOW_MINUTE - minutes, NOW_MINUTE + 1):
        v = after if minute >= onset else before
        jitter = 1 + rng.uniform(-0.03, 0.03)
        points.append([minute_ts(s, minute).isoformat(), round(v * jitter, 4)])
    return {"service": service, "metric": metric, "step": "60s", "points": points}


@app.get("/deploys")
async def deploys(
    service: str | None = None,
    hours: Annotated[int, Query(ge=1, le=72)] = 24,
    x_scenario: Annotated[str | None, Header()] = None,
):
    s = _scn(x_scenario)
    out = []
    for d in s.deploys:
        if service and d["service"] != service:
            continue
        if d["at_minute"] < NOW_MINUTE - hours * 60:
            continue
        out.append({**{k: v for k, v in d.items() if k != "at_minute"},
                    "deployed_at": minute_ts(s, d["at_minute"]).isoformat(),
                    "status": "succeeded"})
    return {"deploys": sorted(out, key=lambda d: d["deployed_at"], reverse=True)}


_ROUTINE_EVENTS = [
    ("Pod", "Scheduled", "Successfully assigned {ns}/{name} to ip-10-4-{a}-{b}.ec2.internal"),
    ("Pod", "Pulled", "Container image \"registry.internal/{name}:sha-{sha}\" already present"),
    ("Pod", "Started", "Started container {name}"),
    ("Node", "NodeHasSufficientMemory", "Node ip-10-4-{a}-{b} status is now: "
                                        "NodeHasSufficientMemory"),
    ("CronJob", "SawCompletedJob", "Saw completed job: {name}-backup-{sha}, status: Complete"),
]


@app.get("/k8s/events")
async def k8s_events(
    namespace: str | None = None,
    x_scenario: Annotated[str | None, Header()] = None,
):
    """Cluster events: the few that matter, buried in routine churn (like `kubectl get ev`)."""
    s = _scn(x_scenario)
    rng = random.Random(f"{s.id}|k8s")
    namespaces = sorted({e["namespace"] for e in s.k8s_events} | {"kube-system", "monitoring"})
    events = [{**{k: v for k, v in e.items() if k != "minute"},
               "time": minute_ts(s, e["minute"]).isoformat(), "type":
               "Warning" if e["reason"] in {"OOMKilled", "BackOff", "Unhealthy",
                                            "FailedGetResourceMetric"} else "Normal"}
              for e in s.k8s_events]
    for _ in range(60):
        kind, reason, msg = rng.choice(_ROUTINE_EVENTS)
        ns = rng.choice(namespaces)
        name = f"{rng.choice(['api', 'worker', 'exporter', 'sidecar'])}-{rng.getrandbits(20):05x}"
        events.append({
            "namespace": ns, "kind": kind, "name": name, "reason": reason, "type": "Normal",
            "message": msg.format(ns=ns, name=name, a=rng.randint(1, 254),
                                  b=rng.randint(1, 254), sha=f"{rng.getrandbits(28):07x}"),
            "time": minute_ts(s, rng.randint(-30, NOW_MINUTE)).isoformat(),
        })
    if namespace:
        events = [e for e in events if e["namespace"] == namespace]
    return {"events": sorted(events, key=lambda e: e["time"])}


@app.get("/dependencies")
async def dependencies(service: str, x_scenario: Annotated[str | None, Header()] = None):
    s = _scn(x_scenario)
    return {"service": service, "depends_on": s.dependencies.get(service, []),
            "depended_on_by": [k for k, v in s.dependencies.items() if service in v]}


@app.get("/runbooks/search")
async def runbook_search(q: str, x_scenario: Annotated[str | None, Header()] = None):
    _scn(x_scenario)
    return {"query": q, "results": runbooks.search(q)}

"""Incident scenarios: the production world the agent investigates, plus ground truth.

Every scenario is deterministic (seeded), so a baseline run and a ScaleDown run of
the same scenario see byte-identical tool outputs. The only variable is the
middleware stack around the agent.

Two scenarios are traps for the circuit breaker:
- `flaky-metrics-loop`: the metrics backend always answers 503 "retry". The
  evidence is still reachable via logs and deploys; an agent that keeps retrying
  metrics is looping.
- `red-herring-drift`: loud, plausible, unrelated signals (TLS expiry, GC pauses,
  an unrelated deploy) pull the agent away from the real DNS cause.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Signal:
    """A log line injected at a minute offset from incident start, repeated `every` mins."""

    service: str
    minute: int
    level: str
    message: str
    every: int = 0  # 0 = once
    until: int = 60


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    kind: str  # clean | loop_trap | drift_trap | context_pressure
    alert: str
    start: datetime  # incident start (minute 0)
    services: tuple[str, ...]
    signals: tuple[Signal, ...]
    deploys: tuple[dict, ...]
    k8s_events: tuple[dict, ...]
    # service -> metric -> (baseline value, value after onset, onset minute)
    metrics: dict[str, dict[str, tuple[float, float, int]]]
    dependencies: dict[str, list[str]]
    root_cause: str
    # Grading: the report's root_cause must hit at least one term from EVERY group.
    keyword_groups: tuple[tuple[str, ...], ...]
    flaky_endpoints: frozenset[str] = frozenset()
    log_lines_per_minute: int = 18
    noise: dict[str, list[tuple[str, str]]] = field(default_factory=dict)


T0 = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)

_DB_POOL_SIGNALS = (
    Signal("payments-api", 2, "ERROR",
           'pq: remaining connection slots are reserved for non-replication superuser '
           'connections db=payments-db pool_size=10 worker_pid={pid}', every=1),
    Signal("payments-api", 2, "WARN",
           "sqlalchemy.pool: QueuePool limit of size 10 overflow 0 reached, connection "
           "timed out, timeout 5.00 worker_pid={pid}", every=1),
    Signal("payments-api", -2, "INFO",
           "gunicorn: booting worker with pid {pid} (workers=16, threads=1)"),
    Signal("checkout-api", 2, "ERROR",
           "upstream payments-api returned 503 Service Unavailable path=/v1/charge "
           "trace_id={trace} latency_ms=5004", every=1),
    Signal("checkout-api", 3, "WARN",
           "circuit breaker payments-api half-open, failure_rate=0.41 window=60s", every=4),
    Signal("payments-db", 2, "FATAL",
           'remaining connection slots are reserved for non-replication superuser '
           'connections (max_connections=100, in use=100) client=payments-api', every=1),
)

_DB_POOL_DEPLOYS = (
    {"id": "dep-7781", "service": "payments-api", "version": "v2.14.0",
     "at_minute": -2, "author": "r.okafor",
     "summary": "Scale gunicorn workers 4 -> 16 for Black Friday load test; SQLAlchemy "
                "pool_size stays 10 per worker.",
     "files_changed": ["deploy/gunicorn.conf.py", "helm/values-prod.yaml"]},
    {"id": "dep-7779", "service": "web-frontend", "version": "v8.3.1",
     "at_minute": -45, "author": "j.li",
     "summary": "Copy change on the cart page; no backend changes.",
     "files_changed": ["src/pages/cart.tsx"]},
)

_COMMON_NOISE = {
    "checkout-api": [
        ("INFO", "request ok method=GET path=/v1/cart/{cart} status=200 latency_ms={lat} "
                 "trace_id={trace}"),
        ("INFO", "request ok method=POST path=/v1/cart/{cart}/items status=201 "
                 "latency_ms={lat} trace_id={trace}"),
        ("DEBUG", "feature flags evaluated user={user} flags=checkout.v2_ui:on,"
                  "checkout.applepay:on cache=hit"),
        ("WARN", "slow request path=/v1/cart/{cart} latency_ms={slow} threshold_ms=800"),
    ],
    "payments-api": [
        ("INFO", "charge authorized order={order} amount_cents={amt} psp=adyen "
                 "latency_ms={lat} trace_id={trace}"),
        ("INFO", "healthcheck ok db=payments-db replicas=2"),
        ("DEBUG", "idempotency key hit key={trace} order={order}"),
    ],
    "payments-db": [
        ("INFO", "checkpoint complete: wrote {n} buffers (0.{lat}%); 0 WAL file(s) added"),
        ("LOG", "duration: {slow}.{n} ms  statement: SELECT * FROM charges WHERE order_id=$1"),
        ("LOG", "connection received: host=10.4.{n}.{lat} port=5432"),
    ],
    "web-frontend": [
        ("INFO", "GET /cart 200 {lat}ms ua=Mozilla/5.0"),
    ],
}

SCENARIOS: dict[str, Scenario] = {}


def _register(s: Scenario) -> None:
    SCENARIOS[s.id] = s


_register(Scenario(
    id="db-pool-exhaustion",
    title="Checkout 5xx: payments DB connection exhaustion",
    kind="clean",
    alert=("[FIRING:1] SEV2 CheckoutHighErrorRate\n"
           "service=checkout-api region=us-east-1 env=prod\n"
           "Error rate 14.2% (threshold 2%) for 5m, started 2026-10-13T10:02Z.\n"
           "Customers report 'Payment could not be processed'. "
           "On-call: find root cause and recommend remediation."),
    start=T0,
    services=("checkout-api", "payments-api", "payments-db", "web-frontend"),
    signals=_DB_POOL_SIGNALS,
    deploys=_DB_POOL_DEPLOYS,
    k8s_events=(
        {"minute": -2, "namespace": "payments", "kind": "Deployment", "name": "payments-api",
         "reason": "ScalingReplicaSet", "message": "Scaled up replica set payments-api-7d9f to 2"},
        {"minute": 5, "namespace": "payments", "kind": "Pod", "name": "payments-api-7d9f-x2k",
         "reason": "Unhealthy", "message": "Readiness probe failed: HTTP probe failed with "
                                           "statuscode: 503"},
    ),
    metrics={
        "checkout-api": {"error_rate": (0.004, 0.142, 2), "p99_latency_ms": (310, 5010, 2),
                         "rps": (820, 805, 99)},
        "payments-api": {"error_rate": (0.002, 0.39, 2), "p99_latency_ms": (180, 5003, 2),
                         "rps": (410, 402, 99)},
        "payments-db": {"active_connections": (38, 100, 0), "cpu_pct": (22, 31, 2),
                        "max_connections": (100, 100, 99)},
    },
    dependencies={"checkout-api": ["payments-api", "inventory-api", "redis-cart"],
                  "payments-api": ["payments-db", "adyen-psp"],
                  "web-frontend": ["checkout-api"]},
    root_cause=("payments-api deploy dep-7781 (v2.14.0) raised gunicorn workers 4->16 with "
                "pool_size 10 each: 160 possible connections against payments-db "
                "max_connections=100, exhausting DB connection slots."),
    keyword_groups=(("payments-api", "payments api"),
                    ("connection", "pool", "max_connections"),
                    ("dep-7781", "v2.14", "workers", "worker", "gunicorn")),
    noise=_COMMON_NOISE,
))

_register(Scenario(
    id="flaky-metrics-loop",
    title="Checkout 5xx with a flapping metrics backend (loop trap)",
    kind="loop_trap",
    alert=SCENARIOS["db-pool-exhaustion"].alert,
    start=T0,
    services=SCENARIOS["db-pool-exhaustion"].services,
    signals=_DB_POOL_SIGNALS,
    deploys=_DB_POOL_DEPLOYS,
    k8s_events=SCENARIOS["db-pool-exhaustion"].k8s_events,
    metrics=SCENARIOS["db-pool-exhaustion"].metrics,
    dependencies=SCENARIOS["db-pool-exhaustion"].dependencies,
    root_cause=SCENARIOS["db-pool-exhaustion"].root_cause,
    keyword_groups=SCENARIOS["db-pool-exhaustion"].keyword_groups,
    flaky_endpoints=frozenset({"metrics"}),
    noise=_COMMON_NOISE,
))

_register(Scenario(
    id="bad-feature-flag",
    title="Search latency: feature flag sends 100% traffic to an under-provisioned reranker",
    kind="clean",
    alert=("[FIRING:1] SEV2 SearchLatencySLOBurn\n"
           "service=search-api region=eu-west-1 env=prod\n"
           "p99 latency 4.8s (SLO 600ms), 5xx 6.1%, error budget burn 14x, since "
           "2026-10-13T14:31Z. Find root cause."),
    start=datetime(2026, 10, 13, 14, 30, tzinfo=UTC),
    services=("search-api", "reranker", "search-index", "flagd"),
    signals=(
        Signal("flagd", 1, "INFO",
               "flag updated key=search.semantic_rerank variant=on rollout=100% "
               "(was 5%) actor=m.santos change_id=FLG-2291"),
        Signal("search-api", 1, "ERROR",
               "rerank call failed: POST http://reranker:8080/rerank: context deadline "
               "exceeded (timeout 2s) query_id={trace}", every=1),
        Signal("search-api", 2, "WARN",
               "falling back to BM25 ordering after rerank failure query_id={trace}", every=1),
        Signal("reranker", 2, "ERROR",
               "torch.OutOfMemoryError: CPU allocator failed to allocate 1.9 GiB "
               "(batch=64, max_seq=512)", every=3),
        Signal("reranker", 3, "WARN", "request queue depth 1840 > 200, shedding load", every=2),
    ),
    deploys=(
        {"id": "dep-8120", "service": "search-index", "version": "v5.2.0", "at_minute": -180,
         "author": "a.ng", "summary": "Nightly index schema bump (adds `brand_vec` field).",
         "files_changed": ["schema/products.json"]},
    ),
    k8s_events=(
        {"minute": 2, "namespace": "search", "kind": "Pod", "name": "reranker-5c8d-0",
         "reason": "OOMKilled", "message": "Container reranker exceeded memory limit 2Gi"},
        {"minute": 5, "namespace": "search", "kind": "Pod", "name": "reranker-5c8d-1",
         "reason": "BackOff", "message": "Back-off restarting failed container reranker"},
        {"minute": 6, "namespace": "search", "kind": "HorizontalPodAutoscaler",
         "name": "reranker", "reason": "FailedGetResourceMetric",
         "message": "maxReplicas=2 reached; desired 11"},
    ),
    metrics={
        "search-api": {"p99_latency_ms": (420, 4800, 1), "error_rate": (0.003, 0.061, 1),
                       "rps": (2300, 2290, 99)},
        "reranker": {"memory_mib": (900, 2048, 2), "rps": (115, 2290, 1),
                     "restarts": (0, 9, 2)},
    },
    dependencies={"search-api": ["reranker", "search-index", "flagd"]},
    root_cause=("Feature flag search.semantic_rerank was rolled out from 5% to 100% "
                "(FLG-2291); the reranker (maxReplicas=2, 2Gi limit) was OOMKilled under "
                "20x traffic, so search-api rerank calls time out."),
    keyword_groups=(("semantic_rerank", "feature flag", "flag", "flg-2291", "rollout"),
                    ("oom", "memory", "reranker")),
    noise={
        "search-api": [
            ("INFO", "query ok q_len={n} hits={amt} latency_ms={lat} query_id={trace}"),
            ("DEBUG", "cache miss key=q:{trace}"),
        ],
        "reranker": [("INFO", "rerank ok batch={n} latency_ms={lat}")],
        "search-index": [("INFO", "segment merge complete segments={n} took_ms={slow}")],
        "flagd": [("DEBUG", "flag eval key=search.typeahead variant=on user={user}")],
    },
))

_register(Scenario(
    id="red-herring-drift",
    title="Login failures: CoreDNS stub-domain removed (drift trap)",
    kind="drift_trap",
    alert=("[FIRING:1] SEV1 AuthLoginFailures\n"
           "service=auth-api region=us-east-1 env=prod\n"
           "Login success rate 61% (SLO 99.5%) since 2026-10-13T08:15Z. "
           "SSO users affected; password logins OK. Find root cause."),
    start=datetime(2026, 10, 13, 8, 15, tzinfo=UTC),
    services=("auth-api", "edge-gateway", "coredns", "marketing-site"),
    signals=(
        Signal("auth-api", 0, "ERROR",
               'oidc discovery failed: Get "https://idp.internal/.well-known/'
               'openid-configuration": dial tcp: lookup idp.internal on 10.96.0.10:53: '
               'no such host', every=1),
        Signal("auth-api", 0, "WARN", "SSO login rejected user={user} reason=idp_unreachable",
               every=1),
        Signal("coredns", -1, "INFO",
               "[INFO] Reloading complete; plugin/reload: Corefile changed, sha=9f1c... "
               "(stub domain internal:53 -> removed)"),
        Signal("coredns", 0, "INFO",
               "[INFO] 10.4.2.17:5133 - A IN idp.internal. udp 41 false 512 NXDOMAIN qr,rd 0.0001s",
               every=1),
        # Red herrings: loud, plausible, unrelated.
        Signal("edge-gateway", 0, "WARN",
               "TLS certificate for *.shop.example.com expires in 9 days "
               "(notAfter=2026-10-22T00:00Z) - rotate soon", every=2),
        Signal("edge-gateway", 0, "ERROR",
               "upstream marketing-site connect timeout path=/promo/fall trace_id={trace}",
               every=3),
        Signal("auth-api", 0, "WARN",
               "GC pause 412ms (G1 Evacuation Pause) heap 1.7G/2G", every=4),
    ),
    deploys=(
        {"id": "dep-6410", "service": "marketing-site", "version": "v3.0.0", "at_minute": -20,
         "author": "c.diaz", "summary": "Fall promo landing pages; new image CDN.",
         "files_changed": ["pages/promo/fall.tsx", "next.config.js"]},
        {"id": "dep-6402", "service": "auth-api", "version": "v4.9.2", "at_minute": -26 * 60,
         "author": "p.kim", "summary": "Bump JWT library 9.0.1 -> 9.0.2 (CVE fix).",
         "files_changed": ["go.mod", "go.sum"]},
    ),
    k8s_events=(
        {"minute": -1, "namespace": "kube-system", "kind": "ConfigMap", "name": "coredns",
         "reason": "Updated", "message": "ConfigMap kube-system/coredns updated by "
                                         "gitops-bot (commit 4e1a7c 'tidy Corefile')"},
        {"minute": 3, "namespace": "web", "kind": "Pod", "name": "marketing-site-6d-q1",
         "reason": "Unhealthy", "message": "Liveness probe failed: timeout"},
        {"minute": 4, "namespace": "auth", "kind": "Pod", "name": "auth-api-88c-j2",
         "reason": "Pulled", "message": "Container image already present on machine"},
    ),
    metrics={
        "auth-api": {"login_success_rate": (0.998, 0.61, 0), "p99_latency_ms": (95, 140, 0),
                     "jvm_gc_pause_ms_p99": (380, 410, 99)},
        "coredns": {"nxdomain_rate": (0.01, 0.37, 0), "qps": (5400, 5600, 0)},
        "edge-gateway": {"error_rate": (0.004, 0.011, 0)},
    },
    dependencies={"auth-api": ["idp.internal (OIDC)", "auth-db", "coredns"],
                  "edge-gateway": ["auth-api", "marketing-site", "checkout-api"]},
    root_cause=("A gitops change to the kube-system/coredns ConfigMap (commit 4e1a7c) removed "
                "the `internal` stub domain, so auth-api cannot resolve idp.internal "
                "(NXDOMAIN) and OIDC/SSO logins fail."),
    keyword_groups=(("dns", "coredns", "nxdomain", "no such host", "resolve"),
                    ("configmap", "corefile", "stub", "idp.internal", "4e1a7c")),
    noise={
        "auth-api": [("INFO", "password login ok user={user} latency_ms={lat}"),
                     ("INFO", "token refreshed user={user} ttl=3600")],
        "edge-gateway": [("INFO", "GET /api/v1/session 200 {lat}ms upstream=auth-api")],
        "coredns": [("INFO", "[INFO] 10.4.{n}.{lat}:{amt} - A IN payments-api.payments.svc."
                             "cluster.local. udp 60 false 512 NOERROR qr,aa,rd 0.0002s")],
        "marketing-site": [("INFO", "render /promo/fall 200 {slow}ms")],
    },
))

_register(Scenario(
    id="log-flood",
    title="Stale inventory: Kafka consumer rebalance storm (context pressure)",
    kind="context_pressure",
    alert=("[FIRING:1] SEV2 InventoryConsumerLag\n"
           "service=inventory-consumer region=us-east-1 env=prod\n"
           "Consumer group inventory-sync lag 2.1M messages and growing since "
           "2026-10-13T12:00Z; storefront shows items in stock that are sold out."),
    start=datetime(2026, 10, 13, 12, 0, tzinfo=UTC),
    services=("inventory-consumer", "kafka", "inventory-api"),
    signals=(
        Signal("inventory-consumer", 1, "WARN",
               "consumer poll timeout has expired. This means the time between subsequent "
               "calls to poll() was longer than the configured max.poll.interval.ms "
               "(300000), member=inventory-sync-{n}", every=2),
        Signal("inventory-consumer", 1, "INFO",
               "Revoking previously assigned partitions [orders-{n}] for group inventory-sync",
               every=1),
        Signal("inventory-consumer", 1, "INFO",
               "processed batch records=5000 took_ms={slowbig} member=inventory-sync-{n}",
               every=1),
        Signal("kafka", 1, "INFO",
               "[GroupCoordinator 2]: Preparing to rebalance group inventory-sync in state "
               "PreparingRebalance with old generation {gen} (reason: removing member "
               "inventory-sync-{n} on heartbeat expiration)", every=1),
    ),
    deploys=(
        {"id": "dep-9002", "service": "inventory-consumer", "version": "v1.31.0",
         "at_minute": -10, "author": "s.ivanova",
         "summary": "Throughput tuning: max.poll.records 500 -> 5000; adds per-record "
                    "warehouse lookup (sync HTTP).",
         "files_changed": ["config/consumer.properties", "src/sync/worker.py"]},
    ),
    k8s_events=(
        {"minute": -10, "namespace": "inventory", "kind": "Deployment",
         "name": "inventory-consumer", "reason": "ScalingReplicaSet",
         "message": "Scaled up replica set inventory-consumer-55f to 6"},
    ),
    metrics={
        "inventory-consumer": {"consumer_lag": (1200, 2_100_000, 1),
                               "rebalances_per_min": (0, 4, 1),
                               "batch_duration_ms_p99": (4000, 340_000, 1)},
        "kafka": {"under_replicated_partitions": (0, 0, 99)},
    },
    dependencies={"inventory-consumer": ["kafka", "warehouse-api"],
                  "inventory-api": ["inventory-db"]},
    root_cause=("Deploy dep-9002 raised max.poll.records 500->5000 with a synchronous "
                "per-record lookup, so batches exceed max.poll.interval.ms (300s); members "
                "are evicted and the group rebalances continuously, stalling consumption."),
    keyword_groups=(("max.poll", "poll interval", "poll()", "rebalanc"),
                    ("max.poll.records", "5000", "batch", "dep-9002")),
    log_lines_per_minute=45,
    noise={
        "inventory-consumer": [
            ("DEBUG", "record ok topic=orders partition={n} offset={amt}{lat} sku=SKU-{order}"),
            ("INFO", "warehouse lookup sku=SKU-{order} took_ms={lat}"),
        ],
        "kafka": [("INFO", "[Log partition=orders-{n}, dir=/var/kafka] Rolled new log segment "
                           "at offset {amt}{lat} in {n} ms.")],
        "inventory-api": [("INFO", "GET /v1/stock/SKU-{order} 200 {lat}ms")],
    },
))


def scenario(scenario_id: str) -> Scenario:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as e:
        raise KeyError(f"unknown scenario {scenario_id!r}; have {sorted(SCENARIOS)}") from e


def minute_ts(s: Scenario, minute: int) -> datetime:
    return s.start + timedelta(minutes=minute)

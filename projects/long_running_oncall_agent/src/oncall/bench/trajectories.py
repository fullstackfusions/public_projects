"""Hand-labeled agent trajectories for the loop/drift classifier comparison.

Each case is (alert, steps, label). Steps are (tool, args, result-preview) as the
circuit breaker's digest renders them. Cases are written to be hard in the ways real
runs are: progressing runs that legitimately call the same tool with different
arguments, loops that vary the arguments slightly, and drift that looks diligent.
"""

from __future__ import annotations

from oncall.agent.guard import digest
from oncall.prodsim.scenarios import SCENARIOS

CHECKOUT = SCENARIOS["db-pool-exhaustion"].alert
SEARCH = SCENARIOS["bad-feature-flag"].alert
AUTH = SCENARIOS["red-herring-drift"].alert
KAFKA = SCENARIOS["log-flood"].alert

E503 = "HTTP 503 from /metrics: {\"error\":\"metrics backend temporarily unavailable " \
       "(thanos-query: context deadline exceeded). Retry later.\"}"


def _s(tool: str, result: str, **args) -> dict:
    return {"tool": tool, "args": args, "result": result}


CASES: list[tuple[str, str, list[dict]]] = [
    # --- progressing -------------------------------------------------------------------
    ("progressing", CHECKOUT, [
        _s("query_logs", "# logs service=checkout-api ... ERROR upstream payments-api returned 503",
           service="checkout-api", level="ERROR"),
        _s("get_dependencies", '{"depends_on": ["payments-api", "inventory-api"]}',
           service="checkout-api"),
        _s("query_logs", "ERROR payments-api pq: remaining connection slots are reserved",
           service="payments-api", level="ERROR"),
        _s("list_deploys", '{"deploys": [{"id": "dep-7781", "service": "payments-api", '
                           '"summary": "Scale gunicorn workers 4 -> 16"}]}',
           service="payments-api"),
    ]),
    ("progressing", CHECKOUT, [
        _s("get_metrics", '{"metric": "error_rate", "points": [[..., 0.142]]}',
           service="checkout-api", metric="error_rate"),
        _s("get_metrics", '{"metric": "error_rate", "points": [[..., 0.39]]}',
           service="payments-api", metric="error_rate"),
        _s("get_metrics", '{"metric": "active_connections", "points": [[..., 100]]}',
           service="payments-db", metric="active_connections"),
        _s("search_runbooks", "RB-101 Postgres: connection exhaustion ...",
           query="remaining connection slots reserved"),
    ]),
    ("progressing", SEARCH, [
        _s("query_logs", "ERROR search-api rerank call failed: context deadline exceeded",
           service="search-api", level="WARN"),
        _s("query_logs", "ERROR reranker torch.OutOfMemoryError ...", service="reranker",
           level="ERROR"),
        _s("get_k8s_events", '[{"reason": "OOMKilled", "name": "reranker-5c8d-0"}]',
           namespace="search"),
        _s("query_logs", "INFO flagd flag updated key=search.semantic_rerank rollout=100%",
           service="flagd"),
    ]),
    ("progressing", AUTH, [
        _s("query_logs", "ERROR auth-api oidc discovery failed: lookup idp.internal: no such host",
           service="auth-api", level="ERROR"),
        _s("query_logs", "[INFO] A IN idp.internal. NXDOMAIN", service="coredns"),
        _s("get_k8s_events", '[{"kind": "ConfigMap", "name": "coredns", "reason": "Updated"}]',
           namespace="kube-system"),
    ]),
    ("progressing", KAFKA, [
        _s("query_logs", "WARN consumer poll timeout has expired ... max.poll.interval.ms",
           service="inventory-consumer", level="WARN"),
        _s("query_logs", "INFO [GroupCoordinator 2]: Preparing to rebalance group inventory-sync",
           service="kafka", contains="rebalance"),
        _s("list_deploys", '{"deploys": [{"id": "dep-9002", "summary": "max.poll.records 500 -> '
                           '5000"}]}', service="inventory-consumer"),
    ]),
    ("progressing", CHECKOUT, [  # same tool four times, but each call is new information
        _s("query_logs", "ERROR upstream payments-api returned 503", service="checkout-api",
           level="ERROR"),
        _s("query_logs", "ERROR pq: remaining connection slots are reserved",
           service="payments-api", level="ERROR"),
        _s("query_logs", "FATAL remaining connection slots ... in use=100", service="payments-db",
           level="ERROR"),
        _s("query_logs", "INFO gunicorn: booting worker with pid 4103 (workers=16)",
           service="payments-api", contains="gunicorn"),
    ]),
    ("progressing", SEARCH, [
        _s("list_deploys", '{"deploys": [{"id": "dep-8120", "service": "search-index"}]}',
           hours=24),
        _s("query_logs", "ERROR rerank call failed: context deadline exceeded",
           service="search-api", level="ERROR"),
        _s("get_dependencies", '{"depends_on": ["reranker", "search-index", "flagd"]}',
           service="search-api"),
        _s("get_metrics", '{"metric": "rps", "points": [[..., 115], [..., 2290]]}',
           service="reranker", metric="rps"),
    ]),
    ("progressing", AUTH, [
        _s("search_runbooks", "RB-330 Auth: SSO/OIDC login failures ... check name resolution",
           query="SSO login failures oidc"),
        _s("query_logs", "ERROR oidc discovery failed: no such host", service="auth-api",
           contains="oidc"),
        _s("search_runbooks", "RB-305 Kubernetes DNS (CoreDNS) failures ...",
           query="no such host coredns"),
    ]),
    # --- looping -------------------------------------------------------------------------
    ("looping", CHECKOUT, [
        _s("query_logs", "ERROR upstream payments-api returned 503", service="checkout-api"),
        _s("get_metrics", E503, service="payments-db", metric="active_connections"),
        _s("get_metrics", E503, service="payments-db", metric="active_connections"),
        _s("get_metrics", E503, service="payments-db", metric="active_connections"),
    ]),
    ("looping", CHECKOUT, [  # varies args slightly, same failure
        _s("get_metrics", E503, service="payments-db", metric="active_connections", minutes=60),
        _s("get_metrics", E503, service="payments-db", metric="active_connections", minutes=30),
        _s("get_metrics", E503, service="payments-db", metric="active_connections", minutes=15),
        _s("get_metrics", E503, service="payments-db", metric="connections", minutes=15),
    ]),
    ("looping", CHECKOUT, [
        _s("get_metrics", E503, service="checkout-api", metric="error_rate"),
        _s("get_metrics", E503, service="payments-api", metric="error_rate"),
        _s("get_metrics", E503, service="payments-db", metric="cpu_pct"),
        _s("get_metrics", E503, service="checkout-api", metric="p99_latency_ms"),
        _s("get_metrics", E503, service="payments-api", metric="error_rate"),
    ]),
    ("looping", SEARCH, [
        _s("query_logs", "# logs service=search ... matched=0 returned=0", service="search"),
        _s("query_logs", "HTTP 404 from /logs: unknown service 'search-service'",
           service="search-service"),
        _s("query_logs", "# logs service=search ... matched=0 returned=0", service="search"),
        _s("query_logs", "HTTP 404 from /logs: unknown service 'search-service'",
           service="search-service"),
    ]),
    ("looping", AUTH, [
        _s("search_runbooks", "RB-330 Auth: SSO/OIDC login failures ...", query="login failures"),
        _s("search_runbooks", "RB-330 Auth: SSO/OIDC login failures ...", query="login failure"),
        _s("search_runbooks", "RB-330 Auth: SSO/OIDC login failures ...", query="sso login failed"),
        _s("search_runbooks", "RB-330 Auth: SSO/OIDC login failures ...",
           query="login failures auth"),
    ]),
    ("looping", KAFKA, [
        _s("query_logs", "WARN consumer poll timeout has expired", service="inventory-consumer"),
        _s("query_logs", "WARN consumer poll timeout has expired", service="inventory-consumer"),
        _s("query_logs", "WARN consumer poll timeout has expired", service="inventory-consumer",
           minutes=30),
        _s("query_logs", "WARN consumer poll timeout has expired", service="inventory-consumer",
           minutes=31),
    ]),
    ("looping", CHECKOUT, [
        _s("list_deploys", '{"deploys": []}', service="checkout-api", hours=24),
        _s("list_deploys", '{"deploys": []}', service="checkout-api", hours=48),
        _s("list_deploys", '{"deploys": []}', service="checkout-api", hours=72),
        _s("list_deploys", '{"deploys": []}', service="checkout-api", hours=72),
    ]),
    # --- drifting ------------------------------------------------------------------------
    ("drifting", AUTH, [
        _s("query_logs", "WARN TLS certificate for *.shop.example.com expires in 9 days",
           service="edge-gateway", level="WARN"),
        _s("search_runbooks", "RB-210 TLS certificate expiry and rotation ...",
           query="tls certificate rotation"),
        _s("query_logs", "ERROR upstream marketing-site connect timeout path=/promo/fall",
           service="edge-gateway", contains="marketing"),
        _s("list_deploys", '{"deploys": [{"id": "dep-6410", "service": "marketing-site", '
                           '"summary": "Fall promo landing pages"}]}', service="marketing-site"),
    ]),
    ("drifting", AUTH, [
        _s("query_logs", "WARN auth-api GC pause 412ms (G1 Evacuation Pause) heap 1.7G/2G",
           service="auth-api", contains="GC"),
        _s("get_metrics", '{"metric": "jvm_gc_pause_ms_p99", "points": [[..., 410]]}',
           service="auth-api", metric="jvm_gc_pause_ms_p99"),
        _s("search_runbooks", "no results", query="jvm heap tuning G1"),
        _s("query_logs", "WARN GC pause 398ms", service="auth-api", contains="heap"),
    ]),
    ("drifting", CHECKOUT, [
        _s("list_deploys", '{"deploys": [{"id": "dep-7779", "service": "web-frontend", '
                           '"summary": "Copy change on the cart page"}]}', hours=24),
        _s("query_logs", "INFO GET /cart 200 41ms", service="web-frontend"),
        _s("query_logs", "DEBUG feature flags evaluated checkout.applepay:on",
           service="checkout-api", contains="feature flags"),
        _s("search_runbooks", "RB-102 ... Disabling the Apple Pay flag only helps when Adyen ...",
           query="apple pay flag"),
    ]),
    ("drifting", SEARCH, [
        _s("list_deploys", '{"deploys": [{"id": "dep-8120", "service": "search-index", '
                           '"summary": "Nightly index schema bump"}]}', hours=24),
        _s("query_logs", "INFO segment merge complete segments=12", service="search-index"),
        _s("query_logs", "INFO segment merge complete segments=9", service="search-index",
           level="INFO"),
        _s("search_runbooks", "no results", query="index schema migration brand_vec"),
    ]),
    ("drifting", KAFKA, [
        _s("get_metrics", '{"metric": "under_replicated_partitions", "points": [[..., 0]]}',
           service="kafka", metric="under_replicated_partitions"),
        _s("query_logs", "INFO Rolled new log segment at offset 88123", service="kafka"),
        _s("query_logs", "INFO GET /v1/stock/SKU-123 200 12ms", service="inventory-api"),
        _s("get_k8s_events", '[{"reason": "SawCompletedJob", "name": "api-backup"}]',
           namespace="monitoring"),
    ]),
    ("drifting", CHECKOUT, [
        _s("query_logs", "WARN slow request path=/v1/cart latency_ms=1200", service="checkout-api",
           level="WARN"),
        _s("get_dependencies", '{"depends_on": ["payments-api", "inventory-api", "redis-cart"]}',
           service="checkout-api"),
        _s("query_logs", "INFO redis-cart GET ok", service="redis-cart"),
        _s("get_metrics", "HTTP 404 from /metrics: no metrics for 'redis-cart'",
           service="redis-cart", metric="memory"),
        _s("search_runbooks", "no results", query="redis eviction policy"),
    ]),
]


def labeled_digests() -> list[tuple[str, str]]:
    """(label, digest text) pairs, rendered exactly as the circuit breaker sends them."""
    return [(label, digest(alert, steps)) for label, alert, steps in CASES]

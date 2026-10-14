"""Runbook corpus served by `GET /runbooks/search`.

Deliberately long, prose-heavy, and overlapping, like real wiki pages: most of each
page is boilerplate (ownership, escalation, history), and the useful paragraph is
somewhere in the middle. This is the content query-aware compression is built for.
"""

from __future__ import annotations

import re

_BOILERPLATE = """
## Ownership and escalation

This service is owned by the {team} team. During business hours, page the primary via
the #{team}-oncall channel. Outside business hours the PagerDuty schedule
"{team}-primary" applies, with automatic escalation to "{team}-secondary" after 15 minutes
without acknowledgement, and to the engineering manager after 30 minutes. For SEV1
incidents, open an incident channel with /incident declare and assign an incident
commander before starting remediation. The incident commander is responsible for
status page updates every 30 minutes, even when there is nothing new to report.

## Communication templates

Initial update: "We are investigating elevated errors affecting {area}. Next update in 30
minutes." Mitigation update: "A mitigation has been applied and we are monitoring
recovery." Resolution: "The issue has been resolved. A post-incident review will follow."
Do not speculate about root cause in customer-facing updates. Do not name vendors.

## Change history of this page

- 2024-03: Page created after INC-1182.
- 2024-11: Added dashboards section; removed references to the legacy Nagios checks.
- 2025-06: Migrated alerts from CloudWatch to Prometheus/Alertmanager.
- 2026-02: Reviewed during the quarterly game day; no changes required.

## Related dashboards

Grafana: "{team} / Service overview", "{team} / Dependencies", "Platform / Kubernetes
workloads". Note that dashboard panels lag by up to 60 seconds; for live data query the
metrics API directly.
"""

RUNBOOKS: list[dict[str, str]] = [
    {
        "id": "RB-101",
        "title": "Postgres: connection exhaustion ('remaining connection slots are reserved')",
        "team": "data-platform",
        "area": "database-backed services",
        "body": """
## Symptoms

Clients log `remaining connection slots are reserved for non-replication superuser
connections` or `too many clients already`. The database itself is usually healthy on
CPU and memory; the limiting resource is `max_connections`.

## Diagnosis

1. Compare `active_connections` against `max_connections` for the database. If they are
   equal, the database is saturated on connections, not on compute.
2. Compute the theoretical demand: for every client service, multiply
   `replicas x workers per replica x pool_size (+ max_overflow)`. A frequent cause is a
   deploy that changes the number of worker processes (gunicorn `workers`, uvicorn
   `--workers`, celery concurrency) without lowering the per-process pool size. Each
   worker process holds its own pool.
3. Check recent deploys of every client service in the last two hours, not just the
   service named in the alert. The alerting service is often a victim upstream.

## Remediation

Roll back the deploy that increased connection demand, or lower `pool_size` so that total
demand stays below 80% of `max_connections`. Long-term, place PgBouncer in transaction
mode in front of the database. Do not raise `max_connections` as a first response: each
connection costs memory and the database may then fail on memory instead.
""",
    },
    {
        "id": "RB-102",
        "title": "Checkout: elevated 5xx error rate",
        "team": "checkout",
        "area": "checkout and payments",
        "body": """
## Symptoms

`CheckoutHighErrorRate` fires when more than 2% of checkout requests fail for 5 minutes.

## Diagnosis

checkout-api is an aggregator. It rarely fails on its own; look at which upstream it is
failing on. Logs contain `upstream <service> returned <status>`. The most common upstreams
are payments-api, inventory-api and redis-cart. If the circuit breaker is half-open for an
upstream, that upstream is the place to continue the investigation. Use the dependency
map to find the upstream's own dependencies.

## Remediation

Remediate the failing upstream. Disabling the Apple Pay flag
(`checkout.applepay`) only helps when the Adyen PSP itself is failing, which shows up as
`psp=adyen status=5xx` in payments-api logs.
""",
    },
    {
        "id": "RB-210",
        "title": "TLS certificate expiry and rotation",
        "team": "edge",
        "area": "public endpoints",
        "body": """
## Symptoms

edge-gateway logs `TLS certificate ... expires in N days`. Warnings start at 14 days.
Expiry warnings do not cause errors before `notAfter`; a certificate that has not yet
expired cannot cause login, checkout or API failures.

## Procedure

Certificates are issued by cert-manager. Run the rotation job `edge-cert-rotate` from the
deploy pipeline; it is safe during business hours. Verify with `openssl s_client` against
every edge POP. Rotation is a planned change: schedule it, do not do it during an active
incident unless the certificate has already expired.
""",
    },
    {
        "id": "RB-305",
        "title": "Kubernetes DNS (CoreDNS) failures",
        "team": "platform",
        "area": "service discovery",
        "body": """
## Symptoms

Applications log `lookup <host> on 10.96.0.10:53: no such host` or `i/o timeout`. CoreDNS
logs `NXDOMAIN` for names that used to resolve. Typically only some dependencies fail:
in-cluster `*.svc.cluster.local` names keep working while names served by a stub domain
(for example `*.internal`, forwarded to the corporate resolvers) fail.

## Diagnosis

1. Check CoreDNS logs for `Reloading complete` and the Corefile sha. A reload right
   before the incident is the strongest signal.
2. Check Kubernetes events for updates to `ConfigMap kube-system/coredns`. Changes are
   made by gitops-bot from the platform-config repo; the event names the commit.
3. Confirm that the `internal:53 { forward . 10.0.0.2 10.0.0.3 }` stub block is still present.

## Remediation

Revert the platform-config commit that changed the Corefile and let gitops-bot sync, or
apply the previous ConfigMap manually and run `kubectl -n kube-system rollout restart
deploy/coredns`. Caches in client pods can hold negative answers for up to 30 seconds.
""",
    },
    {
        "id": "RB-330",
        "title": "Auth: SSO/OIDC login failures",
        "team": "identity",
        "area": "login",
        "body": """
## Symptoms

SSO logins fail while password logins succeed. auth-api logs `oidc discovery failed` or
`idp_unreachable`.

## Diagnosis

auth-api fetches the OIDC discovery document from `https://idp.internal` on every key
rotation and every 10 minutes. If that fetch fails, SSO logins fail closed. Check, in
order: name resolution of idp.internal (see RB-305), network policy, then the IdP itself.
GC pauses under 500ms on auth-api are normal and are not a cause of login failures.

## Remediation

Fix the dependency. As a stopgap, the identity team can pin the discovery document via
the `oidc.static_discovery` flag for up to 24 hours.
""",
    },
    {
        "id": "RB-412",
        "title": "Search: latency and reranker capacity",
        "team": "search",
        "area": "search",
        "body": """
## Symptoms

search-api p99 latency above SLO, `rerank call failed ... context deadline exceeded`, and
fallback to BM25 ordering.

## Diagnosis

The reranker is CPU-bound and sized for the experiment cohort only (`maxReplicas=2`,
2Gi memory). Its traffic is gated by the `search.semantic_rerank` flag. Check flagd for
recent changes to that flag's rollout percentage, and Kubernetes events for `OOMKilled`
on reranker pods.

## Remediation

Reduce the `search.semantic_rerank` rollout back to its previous percentage via flagd
(takes effect in under 30 seconds), then scale the reranker before trying again. Do not
just raise the memory limit: queue depth will keep growing at full traffic.
""",
    },
    {
        "id": "RB-520",
        "title": "Kafka consumers: lag and rebalance storms",
        "team": "streaming",
        "area": "event processing",
        "body": """
## Symptoms

Consumer lag grows without bound; consumers log `poll timeout has expired` and
`Revoking previously assigned partitions`; brokers log repeated `Preparing to rebalance`.

## Diagnosis

A member that does not call `poll()` within `max.poll.interval.ms` is evicted, which
triggers a rebalance, which revokes everyone's partitions. If a single batch takes longer
than the interval, the group never stabilises. Compute `max.poll.records x per-record
processing time` and compare with `max.poll.interval.ms`. Recent changes to
`max.poll.records` or to per-record work (for example, adding a synchronous HTTP lookup)
are the usual cause. Broker health (under-replicated partitions) is usually fine.

## Remediation

Roll back the consumer config change, or lower `max.poll.records` until a batch finishes
well within the interval. Raising `max.poll.interval.ms` hides the problem and delays
failure detection.
""",
    },
]


def search(query: str, limit: int = 3) -> list[dict[str, str]]:
    """Fuzzy term-overlap search returning full pages, like most wiki search APIs: it always
    fills `limit` results once anything matches, so the best page arrives with neighbours."""
    terms = {t[:6] for t in re.findall(r"[a-z0-9_.]+", query.lower()) if len(t) > 2}
    scored = []
    for rb in RUNBOOKS:
        text = f"{rb['title']} {rb['body']}".lower()
        scored.append((sum(text.count(t) for t in terms), rb))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] == 0:
        return []
    return [
        {
            "id": rb["id"],
            "title": rb["title"],
            "content": f"# {rb['title']}\n{rb['body']}"
            + _BOILERPLATE.format(team=rb["team"], area=rb["area"]),
        }
        for _, rb in scored[:limit]
    ]

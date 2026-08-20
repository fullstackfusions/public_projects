# SLI/SLO Observability Pipeline

Vendor-neutral SLI/SLO instrumentation pipeline: a small FastAPI service
instrumented with OpenTelemetry, shipping traces/metrics through an OTel
Collector into Prometheus, visualized in Grafana, with SLO burn-rate
alerting via Sloth + Alertmanager.

## Goal

Take a backend app, instrument it, compute p95/p99 latency + error-rate
SLIs, define an actual SLO, visualize it on a dashboard, and fire an alert
when the error budget burns too fast — built by hand with open-source tools
first (rather than starting from a vendor platform like Dynatrace) so the
underlying SLI/SLO concepts — histograms → percentiles, error budgets,
burn-rate alerting — are provably understood independent of any vendor. See
["If this were Dynatrace instead"](#if-this-were-dynatrace-instead) below
for how a managed platform changes the picture.

## Architecture

```
FastAPI backend ──> OpenTelemetry SDK ──> OTel Collector ──> Prometheus ──> Grafana (dashboards + SLO panel)
                                                                  └──> Alertmanager (email)
```

## Tool purposes

- **OpenTelemetry (OTel)** — the instrumentation layer. Vendor-neutral SDK that generates telemetry (traces, metrics, logs) from app code: auto-instruments HTTP requests, plus custom spans/histograms for business logic. Doesn't store or visualize anything — just produces the raw data and ships it out over OTLP (its wire protocol).
- **OTel Collector** — a standalone process that receives OTLP data from the app and routes it wherever it needs to go. Here it re-exports metrics in Prometheus's scrape format. In a bigger deployment it's also where sampling, filtering, batching, and multi-backend fan-out happen without touching app code.
- **Prometheus** — a time-series database + scraper. Polls the Collector's `/metrics` endpoint, stores histogram buckets over time, and answers PromQL queries (`histogram_quantile(0.95, ...)` for p95 latency). Also evaluates alerting/recording rules and forwards firing alerts to Alertmanager.
- **Sloth** — a code generator, not a running service. Takes an SLO spec ("99% of requests under 500ms over 28 days") and generates the Prometheus recording rules + multi-window burn-rate alert rules by hand — that math is fiddly and easy to get wrong, so Sloth encodes the standard Google SRE-book pattern.
- **Alertmanager** — takes alerts *firing* from Prometheus (like Sloth's burn-rate alert) and handles routing/dedup/grouping/silencing, then sends them to email/Slack/PagerDuty. Prometheus decides *when* something's wrong; Alertmanager decides *who hears about it and how*.
- **Grafana** — the dashboard/visualization layer. Queries Prometheus (or other backends) and renders panels: p50/p95/p99 latency, error rate, error-budget burn-down.

Chain, in one line: **OTel instruments → Collector routes → Prometheus stores/computes → Sloth generates the SLO rules Prometheus evaluates → Alertmanager notifies → Grafana visualizes.**

## Stack

| Component         | Role                                                                               |
| :---------------- | :--------------------------------------------------------------------------------- |
| `app/`            | FastAPI service, OTel auto + custom instrumentation (`/api/orders`, `/api/search`) |
| `otel-collector/` | OTLP receiver → Prometheus exporter                                                |
| `prometheus/`     | Scrapes the collector, evaluates both the manual and Sloth-generated burn-rate alert rules |
| `sloth/`          | SLO spec → Prometheus recording + burn-rate alert rules — `sloth generate` run and live-verified, output at `prometheus/rules/orders-slo-rules.yml` |
| `grafana/`        | Dashboards — 8 panels, provisioned and live-verified                               |
| `alertmanager/`   | Routes burn-rate alerts to email via Gmail SMTP (app password kept out of git, see `alertmanager/secrets/README.md`) |
| `loadtest/`       | k6 script to generate traffic with injected slow/error requests                    |

## If this were Dynatrace instead

Everything above is six separately-configured pieces wired together by hand.
Dynatrace SaaS collapses nearly all of it into one vendor stack:

| This pipeline (what you'd remove/replace) | Dynatrace equivalent |
| :--- | :--- |
| `app/telemetry.py` manual OTel SDK setup, `View` boundary fixes | **OneAgent** — auto-injected agent, discovers the process and instruments it with no code changes (still accepts OTLP directly if you want to keep the OTel SDK calls for custom spans) |
| `otel-collector/` (OTLP receiver → Prometheus exporter) | **Removed entirely** — OneAgent talks straight to Dynatrace's backend (Grail), no intermediate collector to run or configure |
| `prometheus/` (storage, PromQL, `rules/*.yml`, the `prometheus-data` volume) | **Grail** — Dynatrace's proprietary storage/query engine, queried via DQL instead of PromQL; no bucket-boundary tuning, no rule files, no "did the volume get wiped" gotchas |
| `sloth/orders-slo.yaml` + `sloth generate` | Built-in **SLO configuration UI** — fill in target %/timeframe in a form, burn rate computed natively; no YAML spec, no separate generation step, no `le` label formatting bugs to hit |
| `alertmanager/` (Gmail SMTP config, app password file, `group_wait`/`repeat_interval` tuning) | Built-in **Davis AI** anomaly detection + notification integrations (Slack/email/PagerDuty/etc.), configured in the UI — no SMTP relay to debug, no notification-log state to reason about across restarts |
| `grafana/provisioning/` (datasource + dashboard JSON, panel-by-panel PromQL) | Built-in **dashboards** — often auto-built from the same OneAgent data before you write a single query |
| `loadtest/k6-script.js` | Unchanged — load testing is orthogonal to the observability vendor either way |

What this project's build actually spent time on — fixing wrong metric
names, coarse histogram buckets, a good/bad inversion in the SLO query, a
float-formatted `le` label, `[5m]`-window cold-start noise, and Alertmanager
notification-log timing — is exactly the class of problem OneAgent's
auto-instrumentation and Grail's managed storage remove by not exposing that
plumbing to you at all. The trade-off is losing that visibility and control:
Dynatrace is SaaS-only pricing, and DQL/Grail don't transfer to any other
tool the way PromQL and OTel do. Building it by hand first, then doing a
short Dynatrace trial pass on the same app, is what proves the underlying
SLI/SLO concepts (histograms → percentiles, error budgets, burn-rate
alerting) are understood independent of the vendor.

### How OneAgent actually gets deployed (it's not a scraper)

Worth being precise here: OneAgent is **push-based instrumentation**, not a
Prometheus-style pull scraper. There's no equivalent of `prometheus.yml`
polling a `/metrics` endpoint — the agent instruments the app process
in-place and pushes telemetry out over HTTPS to the Dynatrace cluster. Two
deployment modes on Kubernetes/OpenShift, and they look very different day
to day:

- **Classic Full Stack (DaemonSet)** — one OneAgent per *node*, not per pod.
  Runs as a privileged DaemonSet and monitors every process/container on
  that node, plus OCP/K8s infra metrics, without touching individual pod
  specs at all. Install once per cluster, everything on the node is covered.
- **Application Monitoring / Cloud Native injection** — the Dynatrace
  Operator runs a mutating webhook that injects an **init container** into
  each app pod at creation time. That init container drops OneAgent's
  instrumentation binaries into a shared volume; the app container then
  picks them up via env vars (`LD_PRELOAD` for native processes,
  `JAVA_TOOL_OPTIONS`-equivalent for JVM, etc.), so the *app's own process*
  becomes instrumented. Nothing stays alive as a persistent sidecar next to
  the app — the injected code runs inside the app's process itself and
  pushes telemetry from there. This is the mode that looks like "a separate
  container in one app's pod" if you only glance at the pod spec (the init
  container), even though it's not scraping anything.

Once telemetry is flowing into Grail either way, SLOs are defined
identically regardless of injection mode — pick any ingested metric, write
the DQL numerator/denominator (or use the guided form), set the target %.
No separate Sloth-equivalent generation step, no rule files, no `le` label
gotchas — that's the whole category of bug this project's build hit that
Dynatrace's managed pipeline sidesteps.

## If this were Datadog instead

Same six pieces, different vendor stack — and a genuinely different
architecture from Dynatrace's, not just a rebrand of the same idea:

| This pipeline (what you'd remove/replace) | Datadog equivalent |
| :--- | :--- |
| `app/telemetry.py` manual OTel SDK setup, `View` boundary fixes | **Datadog APM tracing library** (`ddtrace`, auto-instrumentation similar effort to OTel's) — *or* keep the OTel SDK exactly as-is and point it at the local Datadog Agent's OTLP ingestion endpoint instead of the OTel Collector |
| `otel-collector/` (OTLP receiver → Prometheus exporter) | **Datadog Agent** — not removed like Dynatrace's OneAgent case, just swapped: still a local daemon process apps talk to, still something you deploy and configure, just shipping to Datadog instead of Prometheus |
| `prometheus/` (storage, PromQL, `rules/*.yml`, the `prometheus-data` volume) | Datadog's backend, queried via its own metric query syntax (`avg:metric.name{tag}`) or built via the UI — not an open query language like PromQL or even DQL; more UI-driven than either |
| `sloth/orders-slo.yaml` + `sloth generate` | Built-in **Service Level Objectives** — metric-based or monitor-based SLO, target %, timeframe (7/30/90d or custom), burn rate computed natively; no YAML spec, no generation step |
| `alertmanager/` (Gmail SMTP config, app password file, `group_wait`/`repeat_interval` tuning) | Built-in **Monitors** — alerting + Watchdog anomaly detection, notification integrations configured in the UI; still has its own version of grouping/notification-interval settings to learn, just via a form instead of YAML |
| `grafana/provisioning/` (datasource + dashboard JSON, panel-by-panel PromQL) | Built-in **dashboards**, often auto-suggested per integration |
| `loadtest/k6-script.js` | Unchanged |

The load-bearing difference from the Dynatrace comparison above: **Datadog
doesn't remove the local-agent layer the way OneAgent removes the OTel
Collector.** The Datadog Agent runs as a DaemonSet on Kubernetes/OpenShift —
one per node, same shape as Dynatrace's Classic Full Stack mode — but your
app still needs *some* instrumentation step (either the `ddtrace` library,
which does its own auto-instrumentation similar to
`opentelemetry-instrumentation-fastapi`, or literally the same OTel SDK code
already in `app/telemetry.py`, just pointed at the Agent's OTLP port instead
of the Collector's). There's no equivalent of Dynatrace's zero-code
init-container injection that instruments an unmodified app process from the
outside — Datadog's story is closer to "your own OTel Collector, but it's
Datadog's Agent and it ships to their backend" than to "an agent that
attaches itself to your process with no app-side changes at all." Concretely
for this project: swapping to Datadog would mean deleting `otel-collector/`
and replacing it with a Datadog Agent DaemonSet, but `app/telemetry.py`
survives almost unchanged (`OTEL_EXPORTER_OTLP_ENDPOINT` just points
somewhere else) — a genuinely smaller migration step than the Dynatrace path,
precisely because Datadog kept the same three-tier shape (app → local
daemon → backend) this project already has.

## End-to-End Workflow

The full path anyone should run, in order, with what to expect at each step.
Live-verified multiple times as of 2026-08-19/20, including two full
alert-fires-to-email deliveries.

### Step 0 — Prerequisites

- Docker Desktop running (`docker info` should succeed, not error on a
  missing socket — if Docker Desktop isn't actually started, `docker compose`
  fails with a `dial unix .../docker.sock: connect: no such file or
  directory` error that looks like a config problem but isn't)
- [k6](https://k6.io/) installed (`brew install k6` on macOS) for the load test
- [Sloth](https://sloth.dev/) installed (`brew install sloth-cli` on macOS — the
  binary itself is still called `sloth`; the search result you actually want
  is `sloth-cli`, not the plain `sloth` cask) if you want to generate the
  real multi-window burn-rate rules instead of relying on the hand-written
  `prometheus/rules/manual-burn-rate-alert.yml`

### Step 1 — Start the stack

```bash
cd projects/sli_slo_observability_pipeline
docker compose up --build -d
```

- App: http://localhost:8000 (`/health`, `/api/search?q=...`, `POST /api/orders`, `/docs` for the FastAPI UI)
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Alertmanager: http://localhost:9093

### Step 2 — Pre-flight check

```bash
docker compose ps          # all 5 containers should say "Up"
curl -s http://localhost:8000/health
curl -s http://localhost:9090/api/v1/targets | grep '"health":"up"'
```

If any container isn't up, `docker compose logs <service>` before doing
anything else — no point chasing dashboard weirdness if the pipe itself is
broken. A hand-written burn-rate alert
(`prometheus/rules/manual-burn-rate-alert.yml`, same math as the Sloth spec)
is already loaded and evaluating at this point — no extra step needed to get
alerting working.

### Step 3 — One-time: set up email alerts

Skip this step to just watch metrics/dashboards; do it if you want to see a
real alert email land.

```bash
# 1. Create a Google App Password: https://myaccount.google.com/apppasswords
#    (requires 2-Step Verification on the account)
echo -n "your16charapppassword" > alertmanager/secrets/gmail_app_password

# 2. Edit alertmanager/alertmanager.yml — replace the two placeholder
#    addresses (smtp_from/smtp_auth_username, and the `to:` receiver)
#    with real ones.

docker compose restart alertmanager
```

`repeat_interval` is currently set to **5m** (not a realistic on-call value —
see the comment in `alertmanager/alertmanager.yml`) specifically so you can
watch a second alert email land without waiting hours. Bump it back up
(e.g. `4h`) before treating this as a real deployment.

Details and troubleshooting: `alertmanager/secrets/README.md`.

### Step 4 — Run a real load test

```bash
cd loadtest
k6 run k6-script.js
```

This runs **5 minutes** at 5 orders/s + 20 searches/s (fixed rates, from the
`constant-arrival-rate` scenarios in `k6-script.js`) — 7,500 total requests.

### Step 5 — What to expect after 5 minutes

The app's fault injection is deterministic in _probability_, not exact
values, so expect numbers close to these, not exact:

| Signal                             | Expected                   | Why                                                                      |
| :--------------------------------- | :------------------------- | :----------------------------------------------------------------------- |
| Total requests                     | ~7,500                     | 25 req/s × 300s                                                          |
| Overall request rate               | ~25 req/s                  | 5 (orders) + 20 (search), fixed by k6 config                             |
| Error rate (5xx)                   | ~2%                        | `ERROR_PROBABILITY = 0.02` in `app/main.py`, same for both endpoints     |
| `/api/search` latency              | ~20-150ms range, p50 ~85ms | `random.uniform(0.02, 0.15)` sleep                                       |
| `/api/orders` latency, fast path   | ~50-200ms, p50 ~125ms      | `random.uniform(0.05, 0.2)` base latency, 95% of requests                |
| `/api/orders` latency, slow path   | ~550ms-1.7s                | `SLOW_PATH_PROBABILITY = 0.05` adds `uniform(0.5, 1.5)` on top           |
| `/api/orders` p99 (ms)             | ~1.4-1.7s, not 2-4.5s       | Fixed via an explicit OTel `View` — see `prometheus/README.md` if it reads high |
| Orders SLO success ratio (< 500ms) | **~95%**, not 99%          | Only the 5% slow-path requests should cross 500ms, so success ≈ 1 − 0.05 |
| Burn rate                          | **~5x**                    | `(1 - 0.95) / (1 - 0.99) = 0.05 / 0.01 = 5`                              |

The last two rows are the interesting ones: the SLO target is 99%, but the
app is _designed_ to only hit ~95% — so the pipeline should show a **clearly
failing SLO and a burn rate around 5x**, not near 1x. If you see a success
ratio close to 99% or a burn rate close to 1, something's off (traffic too
short, wrong query, or a code regression) — that's the correctness signal to
watch, not "everything green."

k6's own end-of-run summary gives a ground truth to cross-check against —
look for `http_req_failed` (should be ~2%) and `http_req_duration p(95)`
(should land in the 150-250ms range, blending search + fast-path orders +
a few slow-path orders).

### Step 6 — Cross-check each dashboard panel

Open http://localhost:3000 (admin/admin) → "SLI/SLO Overview" dashboard, and
match each panel against the table above:

- **Request rate by route** → should settle near the 5 and 20 req/s lines
- **Error rate** → should hover near 2% (axis caps at 10% specifically so
  this is visible — on a 0-100% axis, 2% is an invisible hairline)
- **`/api/orders` p50/p95/p99** and **`/api/search` p50/p95/p99** → p50 near
  the fast-path numbers, p95/p99 pulled up by the slow-path tail
- **Orders SLO: 1h success ratio** → should read ~94-95%, colored red/yellow
  given the thresholds (green only above 99%)
- **Error-budget burn rate** → should sit around 5, well above the "1"
  reference line

If a panel shows `NaN` or comes up empty, don't assume it's broken first —
`rate(...[5m])` reads wrong/empty for the first 1-2 minutes right after a
restart or right after traffic starts, because the window is mostly empty.
Give it a couple minutes of sustained traffic before trusting it; if it's
still empty after that, then something's actually wrong.

### Step 7 — Confirm the alert fires and reaches Alertmanager

The manual rule requires the burn rate to stay `> 1` for a full 5 minutes
(`for: 5m` in `prometheus/rules/manual-burn-rate-alert.yml`) before it moves
from `pending` to `firing` in Prometheus:

```bash
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool
# watch the "state" field: inactive -> pending -> firing
```

Once it's `firing`, Prometheus pushes it to Alertmanager. Check Alertmanager
directly — either the UI at http://localhost:9093 (the alert should be
listed under "Alerts") or its API:

```bash
curl -s http://localhost:9093/api/v2/alerts | python3 -m json.tool
```

This confirms delivery to Alertmanager **independent of email** — useful if
you skipped Step 3 and just want to see the routing/grouping/alerting layer
work without setting up SMTP.

If you did set up email (Step 3), Alertmanager adds its own
`group_wait: 30s` before the first notify attempt. Realistic timeline from a
cold start: ~5-6 minutes of sustained breach, then under a minute more to
the actual email. It does **not** require k6 to still be running — once the
underlying `[1h]` SLI window is breached, the alert keeps firing on its own
until traffic recovers. Because `repeat_interval` is 5m (see Step 3), you'll
get a fresh email every ~5 minutes while the alert is still active — no need
to retrigger k6 to see a second one.

If an email never arrives despite Alertmanager showing the alert as active,
check the container logs for the actual SMTP error rather than guessing:

```bash
docker compose logs alertmanager --no-log-prefix | grep -iE "notify|smtp|error"
```

`535 5.7.8 Username and Password not accepted` means the Gmail App Password
is wrong or belongs to a different account than `smtp_auth_username` — see
`alertmanager/secrets/README.md`.

### Step 8 — Make it a stronger demo (optional)

Every run uses the same fault probabilities today, so it always burns budget
the same way. For a better story, temporarily set `SLOW_PATH_PROBABILITY =
0.005` in `app/main.py` and rerun — success ratio should climb to ~99.5%,
burn rate should drop below 1, and the alert should resolve (and, per Step 3,
send a resolved-notification email too, since `send_resolved: true`).
Showing the dashboard react to both a healthy state and a breaching state
(not just always-breaching) is stronger evidence than one static run.

### Optional: generate the real Sloth rules

Requires `sloth-cli` installed (Step 0). Live-verified 2026-08-20 — this
genuinely produces the standard Google SRE-book multi-window burn-rate
pattern (a page-tier alert combining 5m+1h and 30m+6h windows, a ticket-tier
alert combining 2h+1d and 6h+3d), far more sophisticated than the single-
threshold `manual-burn-rate-alert.yml` used earlier for quick testing:

```bash
cd sloth
sloth generate -i orders-slo.yaml -o ../prometheus/rules/orders-slo-rules.yml
```

`promtool check rules` confirms 17 valid rules generated. To pick them up,
either restart Prometheus (`docker compose restart prometheus`) or, since
`--web.enable-lifecycle` is already on, just hit the reload endpoint without
downtime:

```bash
curl -X POST http://localhost:9090/-/reload
```

Both the manual rule and Sloth's generated rules can run side by side (they
use different alert names — `OrdersErrorBudgetBurn` vs
`OrdersLatencySLOBreach` — no conflict) — confirmed via
`curl http://localhost:9090/api/v1/rules` showing all 4 rule groups loaded.
One thing worth noting: Sloth's generated rules use its default 30-day
period unless you add a custom `time_window` to the SLO spec, not the 28d
mentioned in the original spec — cosmetic difference, doesn't change the
burn-rate math meaningfully.

## Status

- [x] FastAPI app instrumented (auto + custom span/histogram) — live-verified
- [x] docker-compose stack (app, collector, Prometheus, Grafana, Alertmanager) — live-verified, all 5 containers healthy
- [x] Sloth SLO spec — `sloth generate` run for real, output validated with `promtool` and loaded into Prometheus alongside the manual rule
- [x] k6 load-test script with injected slow/error paths — ran the real 5-minute scenario end to end
- [x] p95/p99 + error-rate PromQL confirmed against live metric names — see `prometheus/README.md` for 3 real bugs this caught
- [x] Grafana dashboard panels built — 8 panels, every query live-verified
- [x] Alertmanager receiver wired to email — live-verified twice: alert fired, reached Alertmanager, real email delivered
- [ ] Dynatrace trial pass (optional)

## Glossary - key concepts from this project

**k6 load test** — a load-testing tool where you write the traffic pattern as JavaScript (k6-script.js). Ours uses constant-arrival-rate scenarios: "5 orders/sec for 5 minutes" regardless of how long each request takes, which is what makes results reproducible and comparable run-to-run (as opposed to "N virtual users looping as fast as possible," which conflates load with response time).

**What is k6** — an open-source CLI load generator (Grafana Labs project). It spins up virtual users (VUs) executing your script's functions, and prints latency/error percentiles at the end — same role as autocannon or ab, but with a real scripting language instead of flags, which is why it can express "5 rps constant, mixed with 20 rps of a different endpoint" cleanly.

**NaN-on-cold-window caveat** — histogram_quantile(..., rate(metric[5m])) divides the increase in a counter by the whole window duration. If the window is mostly empty (just restarted, or traffic stopped), the numerator and denominator can both be near-zero, and the division produces NaN or a wildly skewed result — not an error, just silently wrong-looking data. It self-resolves once there's a full window's worth of real traffic. Trap for anyone reading a dashboard cold.

**p50 / p95 / p99, and which to pick** — percentiles of a latency distribution. p50 (median) tells you the typical experience; p95/p99 tell you the tail — the worst 5%/1% of requests. Averages hide tail latency because a few very slow requests get diluted by many fast ones; percentiles don't. Which to alert on depends on what you're protecting: p50 for general health, p95 for "is my app usably fast for almost everyone," p99 for stricter user-facing SLAs or when tail latency directly costs money (e.g., timeouts cascading in a dependency chain). Most SLOs are written against p95 or p99, rarely p50, because p50 barely moves even when things are going wrong for a meaningful slice of users.

**Pre-flight (check)** — the sanity pass before trusting any result: confirm every container is actually up and the app/Prometheus are reachable, before investigating dashboard numbers. Catches "the whole stack is down" before you waste time debugging a PromQL query that was never going to return data.

**SLI (Service Level Indicator)** — the actual measured metric, e.g. "% of /api/orders requests under 500ms." Just a number/ratio.

**SLO (Service Level Objective)** — the target for that SLI, e.g. "99% over a rolling 28 days." A promise, not a measurement.

**Error budget** — 1 - SLO objective. At 99%, you're allowed 1% of requests to miss the target before you've "spent" the budget. It's the mechanism that turns a vague uptime goal into a concrete, spendable quantity teams can make tradeoffs against (ship a risky feature vs. play it safe).

**Burn rate** — how fast you're consuming the error budget relative to a sustainable pace. Burn rate of 1 = exhausting the budget exactly at the 28-day boundary. Burn rate of 5 = you'd exhaust a 28-day budget in ~5.6 days if it kept up — which is exactly the ~5.4x we're seeing, a legitimately alert-worthy state.

**Multi-window burn-rate alerting** — the standard SRE pattern (from the Google SRE book) of requiring two burn-rate conditions to both be true (e.g., high burn over 1h and high burn over 5m) before paging, to avoid alerting on a single short blip while still catching genuine fast-burning incidents quickly.

**`group_wait` / `group_interval` / `repeat_interval`** — Alertmanager's three separate timers, easy to conflate. `group_wait` (30s here) is the delay before the *first* notification for a brand-new alert group, giving related alerts a moment to bundle together. `group_interval` (5m here) is how often a group is re-checked for *new* alerts joining it. `repeat_interval` is how long Alertmanager waits before re-sending the *same still-firing* alert — set to 4h in a real deployment, but that means "I retriggered load and got no new email" is often not a bug, it's this timer working as intended (verified live: re-running k6 multiple times against an alert that never resolved produced zero new emails, because it was one continuous incident, not several). To actually see a fresh notification without waiting out the interval, either let the alert genuinely resolve and refire, or fully recreate the Alertmanager container (`docker compose up -d --force-recreate alertmanager`) to clear its in-memory notification log — a plain `restart` isn't enough since the log lives in the container's writable layer and survives it.

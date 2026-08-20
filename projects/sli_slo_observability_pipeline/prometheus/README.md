# SLI queries

Run these in the Prometheus UI (http://localhost:9090) once traffic is flowing
(see `../loadtest/k6-script.js`).

**Confirmed against a live run** (`opentelemetry-instrumentation-fastapi==0.50b0`)
via http://localhost:8889/metrics — two things differed from the initial
draft and are worth flagging since they're easy to get wrong:

- the auto-instrumented HTTP metric is `http_server_duration_milliseconds`
  (not `..._seconds`) — the `le` bucket boundaries and any `histogram_quantile`
  result are in **milliseconds**, so divide by 1000 to compare against a
  500ms SLO threshold in seconds, or just keep the threshold in ms.
- the route label is `http_target` (not `http_route`), and the status label
  is `http_status_code` (not `status`).
- the custom `order_processing_duration_seconds` histogram is genuinely in
  seconds, but only produces useful percentiles once it uses explicit bucket
  boundaries sized for a sub-2s range — see the `View` in `../app/telemetry.py`.
  Without it, OTel's default boundaries (tuned for a 0-10000 scale) put every
  sample in the same bucket.
- `histogram_quantile(..., rate(...[5m]))` right after (re)starting the app
  or right after a burst of traffic is noisy/wrong — `rate()` divides the
  counter increase by the *whole* window, so a `[5m]` range mostly empty of
  real traffic underestimates the rate and skews the quantile. Verified live:
  a 5m-window query returned p95 ≈ 4.1s immediately after a short burst, but
  cross-checking the raw cumulative bucket counts by hand gave ≈ 1.45s, and a
  `[1m]` window (matching how long traffic had actually been running)
  returned 1.4375 — consistent with the manual calc. Give it a full window's
  worth of sustained traffic (the k6 scenarios run 5m for this reason)
  before trusting a `[5m]` query.
- **Changing a histogram's bucket boundaries is a breaking schema change.**
  After adding an explicit `View` to fix the auto-instrumented metric's
  bucket boundaries (`app/telemetry.py`), `histogram_quantile` briefly read
  p99 as ~4.5s — worse than before the fix. Cause: Prometheus's own retained
  history (persisted across restarts via the `prometheus-data` volume) still
  had old-boundary samples inside the `[5m]` query window, and old + new
  boundary sets don't compose — `histogram_quantile` needs one consistent
  bucket schema across the whole window. Not a collector caching issue (the
  collector's live `/metrics` was already clean) — purely Prometheus's
  stored data. Self-resolved once 5+ minutes had passed since the last
  old-boundary sample; any query spanning a boundary-change moment should be
  treated as unreliable until that moment ages out of its window.

```promql
# p95 latency by route (milliseconds)
histogram_quantile(0.95, sum(rate(http_server_duration_milliseconds_bucket[5m])) by (le, http_target))

# p99 latency by route (milliseconds)
histogram_quantile(0.99, sum(rate(http_server_duration_milliseconds_bucket[5m])) by (le, http_target))

# error rate (5xx / total)
sum(rate(http_server_duration_milliseconds_count{http_status_code=~"5.."}[5m]))
  / sum(rate(http_server_duration_milliseconds_count[5m]))

# custom order-processing p95 (seconds)
histogram_quantile(0.95, sum(rate(order_processing_duration_seconds_bucket[5m])) by (le))
```

`rules/` (created by `sloth generate`, see `../sloth/`) holds the recording
and burn-rate alert rules Prometheus loads via `rule_files` in
`prometheus.yml`.

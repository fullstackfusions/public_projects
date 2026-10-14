# Long-running on-call agent: Deep Agents + ScaleDown, measured

A hands-on companion to LangChain's post
[Building long-running agents with ScaleDown and Deep Agents](https://www.langchain.com/blog/building-long-running-agents-with-scaledown-and-deep-agents).
The post claims that small task-specific models ("CDMs") should do an agent's
context housekeeping (summarize, compress, extract, classify) because frontier models
are too slow and expensive for it. This project puts that claim in a realistic
setting and measures it: a durable on-call incident agent, a fake production
environment with traps, and a ledger that records every token and millisecond.

Everything runs locally with `docker compose`. Inference is CPU-only (Ollama in Docker).

## What's in the box

```
                 POST /api/runs                       ┌──────────────┐
  you / bench ──────────────────▶ api ──XADD──▶ redis │ stream +     │
  dashboard  ◀──── SSE ─────────  (FastAPI)    ◀──────│ consumer grp │
                                   │                  └──────┬───────┘
                                   │ events/ledger           │ XREADGROUP / XAUTOCLAIM
                                   ▼                         ▼
                                postgres ◀── checkpoints ── worker ×N ──▶ ollama (CPU)
                                (runs, events,               │  Deep Agent    qwen3:8b agent
                                 ledger, LangGraph           │  + middleware  qwen3:1.7b judge
                                 checkpoints)                │
                                                             ├──HTTP──▶ prodsim (fake prod:
                                                             │          logs, metrics, deploys,
                                                             │          k8s events, runbooks)
                                                             └──HTTPS─▶ ScaleDown API
```

| Service | Role |
|---|---|
| `api` | Creates runs, serves run state, streams timelines over SSE, hosts the dashboard at <http://localhost:8000> |
| `worker` (×2) | Executes runs. Durable: kill one and another resumes the run from its last checkpoint |
| `prodsim` | Deterministic fake production: 5 incident scenarios with ground truth, two of them traps |
| `ollama` + `ollama-pull` | CPU inference; reuses models from `~/.ollama/models` on the host |
| `postgres` | LangGraph checkpointer + `runs`, `run_events`, `ledger` |
| `redis` | Run queue (Streams + consumer group, AOF on) and live event fan-out |
| `bench` | One-shot measurement runners (profile `bench`) |

### Scenarios

| id | kind | what makes it hard |
|---|---|---|
| `db-pool-exhaustion` | clean | Symptom in checkout-api, cause is a payments-api deploy two hops upstream |
| `bad-feature-flag` | clean | Cause is a flag rollout, visible only in flagd logs + k8s OOM events |
| `flaky-metrics-loop` | **loop trap** | Metrics backend always answers `503 … Retry later`; evidence is still in logs/deploys |
| `red-herring-drift` | **drift trap** | Loud, plausible, unrelated signals (TLS expiry, GC pauses, a frontend deploy) vs a quiet CoreDNS change |
| `log-flood` | context pressure | Kafka rebalance storm buried in high-volume logs |

### Middleware profiles

Profiles are frozen into each run's row, so every result traces back to exactly what was on.

| profile | summarizer | tool compression | log fold | extraction | guard |
|---|---|---|---|---|---|
| `baseline` | local (agent model) | – | – | – | shadow (records only) |
| `scaledown` | ScaleDown, local fallback | ScaleDown | – | ScaleDown | enforce (ScaleDown classify) |
| `scaledown_fold` | ScaleDown, local fallback | ScaleDown | ✓ | ScaleDown | enforce |
| `baseline_naive`, `scaledown_naive` | same as `baseline` / `scaledown`, minus the prompt sentence telling the agent not to retry failing tools (for loop-trap experiments) | | | | |
| `fold_only`, `guard_*` | ablations, one change at a time | | | | |

## Quickstart

**Prerequisites:** Docker Desktop, `make`, and a ScaleDown API key
([free tier](https://scaledown.ai/dashboard)). `uv` is only needed for `make screenshots`.

```bash
cd projects/long_running_oncall_agent
make env        # creates .env from .env.example; never overwrites an existing .env
                # -> put your key in it:  SCALEDOWN_API_KEY=...
make doctor     # checks Docker memory, keys, cached models and ports; tells you which `up` to use
```

Then start the stack in **one** of these ways:

| command | when | agent model / context | workers |
|---|---|---|---|
| `make up` | Docker Desktop memory **≥ 16 GB** (used for all published numbers) | qwen3:8b on CPU, 32k | 2 |
| `make up-lite` | Docker Desktop at the default **8 GB** | qwen3:8b on CPU, 16k | 1 |
| `make up-metal` | dev only: native Ollama app on the Mac (Metal GPU), not for published numbers | your host Ollama | 2 |

```bash
open http://localhost:8000      # pick a scenario + profile, "Page the agent"
make run                        # ...or from the CLI (SCENARIO=... PROFILE=... optional)
make logs                       # follow the workers
make chaos                      # kill a worker mid-run; another resumes it from the checkpoint
make down                       # stop everything (data volumes are kept)
make clean                      # end of testing: also delete data volumes + built image (asks first)
```

**What to expect:** the first `make up` builds the image and, if `~/.ollama/models` has no
qwen3 yet, downloads about 6.6 GB (qwen3:8b + qwen3:1.7b). On CPU the first model call
of a run takes about a minute (model load + prefilling the ~4k-token system prompt);
later calls take 5–90 s. An incident run takes about 10–30 minutes. That is the CPU-only
setting, not a hang.

> **Docker memory:** `make up` on an 8 GB Docker Desktop does not crash, it stalls:
> qwen3:8b at 32k needs about 8.1 GB (5.2 GB weights + 2.4 GB KV cache), so the weights
> page in and out, the Ollama container sits at 0% CPU, and the run stays at step 0. Use
> `make up-lite`, or raise memory in Docker Desktop → Settings → Resources and run `make up`.

For `make up-metal`, install and start the [Ollama app](https://ollama.com/download), then
`ollama pull qwen3:8b`. The container Ollama publishes on host port **11435**, so it never
collides with a native Ollama on 11434. Override it with `OLLAMA_HOST_PORT`.

### Troubleshooting

| symptom | cause | fix |
|---|---|---|
| run stuck at `running · 0 steps`, `docker stats` shows ollama near its memory limit at ~0% CPU | not enough Docker memory for the context size | `make down && make up-lite`, or give Docker ≥ 16 GB |
| `model runner has unexpectedly stopped` / `model_retry` events; `docker inspect oncall-ollama-1` shows `OOMKilled=true` | Ollama's model process was OOM-killed (qwen3:8b at 16k uses ~6.4 GB of an 8 GB Docker VM) | Runs retry and recover automatically (3 retries with backoff). For headroom, run one worker (`--scale worker=1`) or give Docker ≥ 12 GB |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | another app (or an old copy of this stack) owns the port | `make doctor` names the process |
| `profile needs ScaleDown but SCALEDOWN_API_KEY is not set` in worker logs | empty key in `.env` | set it, then `docker compose up -d` to reload env |
| worker logs `waiting for model qwen3:8b` | first-time model download still running | `docker compose logs -f ollama-pull` |
| `make frontier` → `429 billing_not_active` | OpenAI account has no active billing | add a payment method at platform.openai.com; `make frontier-dry` is free |

## Design notes worth stealing

- **Durability is two mechanisms, not one.** Redis Streams gives at-least-once delivery;
  the worker heartbeats its pending entry with `XCLAIM … JUSTID`, so a run that legitimately
  takes 20 minutes is not stolen, while a dead worker's entry goes idle and is taken by
  `XAUTOCLAIM`. The new owner resumes the LangGraph thread from its Postgres checkpoint, so
  finished model and tool calls are not repeated (`runs.attempts` > 1 shows it happened).
- **The circuit breaker runs in `before_model`, not `after_model`** (the source post uses the
  latter). There it sees the latest tool result, and an injected nudge lands after the
  `ToolMessage`s instead of between an AI tool call and its result, which breaks the
  tool-calling protocol. Its nudge counter lives in graph state, so it survives a resume.
- **Fail-open is not uniform.** `ScaledownSummarizationMiddleware` fails open, but a
  `ScaledownSummarizer` inside Deep Agents' own summarization middleware raises. We wrap
  it with `.with_fallbacks([local summarizer])` and the ledger records which path ran.
- **Summarization must see the whole history.** Deep Agents trims history to 4,000 tokens
  before summarizing, with `start_on="human"`. An autonomous agent has one human message (the
  alert, at the start), so past 4,000 tokens the window is empty and LangChain substitutes
  "Previous conversation was too long to summarize." No error, findings gone, summarizer never
  called. We pass `trim_tokens_to_summarize=None` and flag any placeholder summary in the
  ledger (`summary_placeholder`).
- **A model-server crash is not a worker crash.** An OOM-killed Ollama runner used to fail the
  run despite an intact checkpoint. `ModelRetryMiddleware` (innermost, 3 retries with backoff)
  turns it into a retry; each one is recorded as `model_retry`.
- **Deep Agents' default subagent is disabled** via a harness profile: its model calls
  would bypass the measurement probe. `execute` is excluded too (no sandbox backend).
- **Explicit summarization trigger.** `ChatOllama` has no model profile, so Deep Agents
  defaults to a 170k-token trigger, far beyond a 32k `num_ctx`. Ollama silently truncates
  the prompt instead of erroring, so without an explicit trigger the baseline degrades
  silently.
- **Measure at the boundary.** `ModelProbeMiddleware` is innermost, so its token counts
  are what actually reaches the model after summarization and schema changes. The
  ScaleDown client is subclassed, so the stock middlewares are used unmodified and still
  measured. Ollama's `prompt_eval_count` (compute spent, excluding KV-cache hits) is
  recorded next to context size.
- **The trap ground truth lives server-side.** prodsim logs every request per run, so
  "calls after the first 503" comes from the wire, not from the agent's account of itself.

## Measuring

```bash
make compress-bench   # tool-output reducers on prodsim outputs (no LLM)
make loghub-bench     # same reducers on real LogHub logs, scored by ground-truth templates
make frontier-dry     # frontier-vs-ScaleDown cost estimate; `make frontier` to spend it
make bench            # end-to-end matrix through the production path (hours on CPU)
make screenshots      # dashboard PNGs, light + dark, into results/screenshots/ (gitignored)
```

Every reported number is an aggregate over `ledger` / `runs` / `run_events` rows or a
labeled dataset. `results/` holds the raw JSON next to each Markdown table.

## Findings so far

Measured 2026-10-13/14 with langchain-scaledown 0.2.0, qwen3:8b on CPU at a 16k context.
Tables and raw JSON are in `results/`.

**1. ScaleDown compress depends on the content type.** On prose runbook pages it cut
1,802 → 229 tokens (−87%) and kept every fact we checked. On logs it behaves differently:

| LogHub system (2k lines) | Drain-style fold | ScaleDown compress | fold → compress |
|---|---|---|---|
| OpenStack | −97%, abnormal 2/2 | −50%, 2/2, 22 s | −99%, **1/2** |
| HDFS | −98%, 1/1 | −81%, 1/1, 9 s | −98%, 1/1 |
| Hadoop | −94%, 12/12 | −98%, **4/12**, 12 s | −99%, **4/12** |
| BGL | −92%, 73/77 | **unchanged** | −94%, **49/77** |
| Apache | −99%, 4/4 | **unchanged** | −99%, 4/4 |
| Zookeeper | −97%, 12/12 | **unchanged** | −97%, 12/12 |

"abnormal" = distinct WARN/ERROR/FATAL ground-truth templates with at least one line kept
verbatim. "unchanged" = ScaleDown returned `successful: true` with the input byte-for-byte
(while reporting ~17% fewer tokens). On Hadoop it dropped 8 of 12 error templates although
the query asked for errors. Caveat: the fold is generic Drain-style masking, but we switched
to it after seeing LogHub results, so treat its numbers as tuned-on-test.

**2. Tool compression depends on the agent model opting in.** The middleware only acts when
the model fills the optional `compression_query` argument. Across every run with it enabled,
qwen3:8b made 55 calls to the four bulky tools and filled it zero times.

**3. No detector is a clean win.** Replaying 21 hand-written trajectories (8 progressing,
7 looping, 6 drifting) at the 0.6 nudge threshold:

| | ScaleDown Classify | Local judge (qwen3:1.7b, CPU) | Heuristic |
|---|---|---|---|
| Top label correct | 17 / 21 | 10 / 21 | n/a |
| False nudges on progressing | 0 / 8 | 4 / 8 | 0 / 8 |
| Loops caught | 4 / 7 | 6 / 7 | 3 / 7 |
| Drift caught | 1 / 6 | 4 / 6 | 0 / 6 |
| Latency | 0.4–7 s | 2.4 s median | ~0 ms |

On a real run that never repeated a call, ScaleDown's top label was "looping" on 10 of 11
checks, peaking at 0.59. The loop trap itself never produced a loop: one prompt sentence
("don't keep retrying a failing tool") was enough on qwen3:8b.

**4. Durability.** A worker killed at step 5 was reclaimed by another worker 86 s later and
resumed after step 5, with no duplicate model-call rows. An OOM-killed Ollama runner failed a
run before `ModelRetryMiddleware` was added; afterwards the same crash cost one retry.

**5. The reasoning model's own confidence is not calibration.** Correct reports claimed 0.95;
a non-answer and a vague report both claimed 1.0.

Not run yet: the frontier side of the cost comparison (`make frontier`) and the full
end-to-end matrix with repeats (`make bench`). Nothing above depends on them.

## Limits

- prodsim is synthetic. Its logs have about 40 templates per service, so folding is not
  trivially easy, but they are still cleaner than real logs, which is why the LogHub
  bench exists.
- Grading is keyword-based: reproducible but strict. One report named the right deploy and
  was graded wrong for describing the mechanism differently. Reports are stored; check them.
- Few end-to-end runs (seven completed, one per cell) at a 16k context: enough to find bugs
  and failure modes, not enough to rank profiles.
- The 21 classifier trajectories are hand-written by the author.
- Token counts use tiktoken cl100k for every model so they are comparable, not exact
  for qwen3.
- Prices come from public catalogs as of 2026-10-13. ScaleDown summarize prices conflict
  across catalogs ($0.02–0.04/1M); we use $0.04.

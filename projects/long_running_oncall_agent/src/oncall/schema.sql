-- Application tables. LangGraph's checkpoint tables are created separately by
-- PostgresSaver.setup() in the same database.

CREATE TABLE IF NOT EXISTS runs (
    id            UUID PRIMARY KEY,
    scenario      TEXT        NOT NULL,
    profile       TEXT        NOT NULL,
    config        JSONB       NOT NULL,          -- resolved profile flags, frozen at enqueue
    alert         TEXT        NOT NULL,
    status        TEXT        NOT NULL DEFAULT 'queued',
    -- queued | running | succeeded | failed | stopped_by_guard | budget_exhausted
    worker        TEXT,
    attempts      INT         NOT NULL DEFAULT 0, -- >1 means it was resumed after a crash
    extraction    JSONB,
    report        JSONB,
    grade         JSONB,
    guard_verdict JSONB,
    error         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS runs_created_idx ON runs (created_at DESC);

-- Human-readable timeline (what the dashboard streams).
CREATE TABLE IF NOT EXISTS run_events (
    id      BIGSERIAL PRIMARY KEY,
    run_id  UUID        NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ts      TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind    TEXT        NOT NULL,
    payload JSONB       NOT NULL
);

CREATE INDEX IF NOT EXISTS run_events_run_idx ON run_events (run_id, id);

-- Measurement ledger: one row per costed operation. Every number in the bench
-- report is an aggregate over this table; nothing is estimated after the fact.
CREATE TABLE IF NOT EXISTS ledger (
    id          BIGSERIAL PRIMARY KEY,
    run_id      UUID        NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    step        INT         NOT NULL,       -- agent model-call index at the time
    component   TEXT        NOT NULL,
    -- agent_model | tool | log_fold | sd_compress | sd_summarize | sd_classify
    -- | sd_extract | local_summarize | local_judge | heuristic_judge
    in_chars    INT,
    out_chars   INT,
    in_tokens   INT,                         -- tiktoken cl100k unless meta.source says otherwise
    out_tokens  INT,
    latency_ms  DOUBLE PRECISION,
    ok          BOOLEAN     NOT NULL DEFAULT true,
    meta        JSONB       NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ledger_run_idx ON ledger (run_id, component);

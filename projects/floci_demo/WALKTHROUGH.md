# Floci document pipeline — walkthrough

End-to-end demo: file upload → S3 → SQS → worker → S3 + DynamoDB, with a Streamlit UI.

## Architecture

```
+-----------+     submit_document()      +--------+
| Streamlit | ────────────────────────▶ |  S3    |  incoming/<job_id>/<file>
|   app.py  |                           +--------+
|           | ────────────────────────▶ |  SQS   |  { job_id, s3_key }
|           |                           +--------+
|           | ────────────────────────▶ | DynamoDB|  status: QUEUED
+-----------+                           +---------+
       │
       │  sidebar button  /  worker.py --loop
       ▼
+------------------+  read  +-----+  write  +---------------------+
| process_next_job | ──────▶ | S3  | ──────▶ | S3 processed/*.json |
+------------------+        +-----+         +---------------------+
       │                                           update
       └───────────────────────────────────▶ DynamoDB: PROCESSED
```

All services run in one Floci container on `http://localhost:4566`.

## Setup

```bash
cd projects/4.floci_demo
conda activate base
pip install -r requirements.txt
docker compose up -d
python bootstrap_resources.py
```

## Run

```bash
streamlit run app.py        # UI at http://localhost:8501
```

Worker daemon (separate terminal):
```bash
conda activate base && python worker.py --loop
```

## Flow

1. **Submit** — fill the form, upload a file (csv/json/md/txt/yml/yaml optional). Creates S3 object + SQS message + DynamoDB row (`QUEUED`).
2. **Process** — click *Process one queued job* in the sidebar, or let `worker.py --loop` pick it up. Reads S3, computes summary (sha256, size, line/word count, preview), writes `processed/<job_id>.json` to S3, updates DynamoDB to `PROCESSED`.
3. **Inspect** — Jobs table shows all DynamoDB rows. Select a job in the dropdown to see the full record and S3 result.
4. **Verify round-trip** — S3 objects panel at the bottom should show both `incoming/<job_id>/<file>` and `processed/<job_id>.json`.

## Things to try

- Upload `.json` → summary includes `top_level_keys`
- Upload `.csv` → line and word counts reflect rows/tokens
- Submit with no file → auto-generates `submission.json` from title + notes
- Stop the worker mid-batch, watch queue depth stay non-zero

## Reset

```bash
docker compose down && rm -rf data
docker compose up -d && python bootstrap_resources.py
```

## Env defaults

```
AWS_ENDPOINT_URL=http://localhost:4566
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

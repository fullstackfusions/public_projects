# floci_demo

Document-processing pipeline demo using **Floci** (local AWS emulator) — S3 + SQS + DynamoDB behind a Streamlit UI.

## Stack

- **Floci** — AWS emulator running on `http://localhost:4566`
- **S3** — stores raw uploads (`incoming/`) and processing results (`processed/`)
- **SQS** — async job queue between UI and worker
- **DynamoDB** — job state tracking
- **Streamlit** — upload UI and job inspector

## Quick start

```bash
cd projects/4.floci_demo
conda activate base
pip install -r requirements.txt

docker compose up -d
python bootstrap_resources.py   # creates bucket, queue, table
streamlit run app.py            # http://localhost:8501
```

Worker (separate terminal):
```bash
conda activate base && python worker.py --loop
```

Backend-only smoke test:
```bash
python smoke_test.py
```

## Reset

```bash
docker compose down
rm -rf data
```

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Floci container |
| `floci_client.py` | boto3 clients pointed at Floci |
| `document_pipeline.py` | All S3 / SQS / DynamoDB logic |
| `bootstrap_resources.py` | One-time resource creation |
| `app.py` | Streamlit frontend |
| `worker.py` | Job processor (`--loop` for daemon mode) |
| `smoke_test.py` | End-to-end backend test |

## Env defaults

```
AWS_ENDPOINT_URL=http://localhost:4566
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

Override any of these to point at a different Floci instance.

# mongodb-distributed-lock

A small reference implementation of a **distributed lock** built on top of MongoDB. Useful when multiple worker instances need to coordinate exclusive access to a resource (e.g. processing the same chat event only once).

## How it works

The `DistributedLock` class uses `find_one_and_update` with `upsert=True` against a `locks` collection. A lock document carries a TTL (`expires_at`); a new acquirer can take over once the previous owner's TTL has passed, which prevents stuck locks if a worker crashes.

## Files

| File | Purpose |
|------|---------|
| `mongodb-distributed-lock.py` | The `DistributedLock` class (`acquire` / `release`) plus a short usage example at the bottom. |
| `distributed-lock-application.py` | Example consumer (`FrontendHandler`) showing how the lock plugs into a Kafka-fronted chatbot pipeline. References external types (`KafkaHandler`, `Message`, `ResponseType`, …) that are sketched, not fully implemented. |

## Prerequisites

- Python 3.9+
- A running MongoDB instance on `localhost:27017`

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python mongodb-distributed-lock.py
```

The script attempts to acquire `"resource_123"`, prints whether it got the lock, and releases it.

## Notes

`distributed-lock-application.py` is illustrative — it references `KafkaHandler`, `Message`, etc. that are not defined in this folder. Treat it as a pattern sketch, not a runnable file.

# mongodb-to-avoid-duplicate

Single-module **`CacheManager`** built on MongoDB that bundles three patterns useful for idempotent request handling:

1. **Caching** of request/response pairs (hashed) so repeats are answered from the cache.
2. **Duplicate request detection** within a short window.
3. **Distributed lock** so only one worker processes a given event at a time.

All three are backed by separate collections with **unique indexes** on the hash field and **TTL indexes** for automatic expiry (5 min for locks/duplicates, 24 h for cached responses).

## Files

| File | Purpose |
|------|---------|
| `mongodb-entry.py` | The full `CacheManager` class with index setup, lock/release helpers, hash generator, and cache get/set. |

## Prerequisites

- Python 3.9+
- A running MongoDB instance on `localhost:27017`

## Install

```bash
pip install -r requirements.txt
```

## Run

This is library code — instantiate `CacheManager` from your application:

```python
from mongodb_entry import CacheManager  # filename: mongodb-entry.py

cm = CacheManager()
if cm.acquire_lock(event_id="abc"):
    try:
        ...  # process the event
    finally:
        cm.release_lock("abc")
```

## Notes

The script references `ResponseForm`, `ResponseText`, `FormRequest`, `TextRequest`, and `ResponseType` from outside — supply your own definitions (see `mongo-orm-structure/` in this repo for one such shape).

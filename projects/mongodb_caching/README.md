# mongodb_caching

A `CacheManager` class that uses **MongoDB as a response cache** keyed by a SHA-256 hash of the request payload. Cached entries are kept for 24 hours; expired entries are filtered out at read time.

Supports both `FormRequest` and `TextRequest` payloads (typed via dataclasses) and stores typed `Response` lists (`ResponseForm`, `ResponseText`).

## Files

| File | Purpose |
|------|---------|
| `mongodb-caching.py` | The full `CacheManager` class with `cache_response` and `get_cached_response`. |

## Prerequisites

- Python 3.9+
- A running MongoDB instance on `localhost:27017`

## Install

```bash
pip install -r requirements.txt
```

## Run

Library-style — import and use:

```python
from mongodb_caching import CacheManager  # filename: mongodb-caching.py

cm = CacheManager()
cached = cm.get_cached_response(request)
if cached is None:
    cached = expensive_computation(request)
    cm.cache_response(request, cached)
```

## Notes

The script references `FormRequest`, `TextRequest`, `ResponseForm`, `ResponseText`, and `ResponseType` from outside — wire in your own dataclasses (the commented-out block at the top of the file shows the expected shape). Companion projects:

- `mongodb-to-avoid-duplicate/` — extends this pattern with locks and duplicate detection.
- `mongo-orm-structure/` — defines a similar request/response domain using `mongoengine`.

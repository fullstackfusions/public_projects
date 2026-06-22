# Task 02 — LRU Cache

Implement `class LRUCache` in `solution.py`.

## API

```python
LRUCache(capacity: int)        # initialize with max capacity
cache.get(key: int) -> int     # return value if exists, else -1
cache.put(key: int, value: int) -> None  # insert/update; evict LRU if full
```

## Rules

- `get` counts as a "use" — promotes the key to most-recently-used
- When at capacity and inserting a new key, evict the **least recently used** key
- `capacity >= 1`
- Do **NOT** use `functools.lru_cache` — implement the data structure yourself

## Files

- `description.md` — this file (read-only)
- `solution.py` — write your implementation here
- `test_solution.py` — tests that must pass (read-only)

## Hint

`collections.OrderedDict` lets you move items to the end and pop from the beginning in O(1).

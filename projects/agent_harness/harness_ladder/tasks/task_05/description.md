# Task 05 — Token Bucket Rate Limiter

Implement `class TokenBucket` in `solution.py`.

## API

```python
TokenBucket(rate: float, capacity: float)
# rate     — tokens refilled per second
# capacity — max tokens the bucket can hold

bucket.acquire(tokens: float = 1.0) -> bool
# Returns True  if tokens were available and consumed
# Returns False if insufficient tokens (does NOT block, does NOT partially consume)
```

## Behavior

- On creation the bucket starts **full** (tokens == capacity)
- Each `acquire` call first refills the bucket based on elapsed real time since the last call, capped at `capacity`
- If after refill the bucket has >= `tokens`, consume them and return `True`
- Otherwise return `False` without consuming anything
- Use `time.time()` for timing — no threading required

## Files

- `description.md` — this file (read-only)
- `solution.py` — write your implementation here
- `test_solution.py` — tests that must pass (read-only)

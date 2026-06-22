# Task 04 — Retry Decorator

Implement `retry` in `solution.py` — a decorator factory.

## Signature

```python
def retry(max_attempts: int = 3, delay: float = 0.0, exceptions: tuple = (Exception,)):
    ...
```

## Behavior

- Retries the decorated function up to `max_attempts` times **total** (first call counts as attempt 1)
- Waits `delay` seconds between attempts using `time.sleep`
- Only catches exceptions listed in `exceptions`; all others propagate immediately
- If all attempts are exhausted, re-raises the **last** exception
- If the function succeeds on any attempt, returns its value immediately — no sleep after success

## Files

- `description.md` — this file (read-only)
- `solution.py` — write your implementation here
- `test_solution.py` — tests that must pass (read-only)

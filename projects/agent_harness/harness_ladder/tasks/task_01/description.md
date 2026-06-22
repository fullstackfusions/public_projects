# Task 01 — Fibonacci with Memoization

Implement `fibonacci(n: int) -> int` in `solution.py`.

## Requirements

- Returns the nth Fibonacci number (0-indexed: fibonacci(0)=0, fibonacci(1)=1, fibonacci(2)=1 ...)
- **Must use memoization** — a plain recursive solution will time out on fibonacci(35)
- Handles n=0 and n=1 correctly
- Raises `ValueError` for n < 0

## Files

- `description.md` — this file (read-only)
- `solution.py` — write your implementation here
- `test_solution.py` — tests that must pass (read-only, do not modify)

## Hint

Use `functools.lru_cache` or a manual dict cache. The tests check both correctness and performance.

# Task 03 — CSV Parser

Implement `parse_csv(text: str) -> list[dict[str, str]]` in `solution.py`.

## Rules

- First line is the **header** row
- Fields are comma-separated
- A field **may be quoted** with double-quotes (`"`)
  - Inside a quoted field, a literal `"` is escaped as `""`
  - A quoted field may contain commas
- Strip leading/trailing whitespace from **unquoted** values only
- Empty input → return `[]`
- Header-only input (no data rows) → return `[]`

## Files

- `description.md` — this file (read-only)
- `solution.py` — write your implementation here
- `test_solution.py` — tests that must pass (read-only)

## Hint

Do NOT use Python's `csv` module — implement the parser yourself. Handle quoted fields character by character.

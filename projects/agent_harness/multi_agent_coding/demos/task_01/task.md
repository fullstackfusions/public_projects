# Email Validator

Implement `validate_email(email: str) -> bool` in `solution.py`.

## Requirements

- Returns `True` for valid email addresses, `False` otherwise
- A valid email has the form `local@domain.tld` where:
  - `local` contains letters, digits, dots, underscores, percent signs, plus signs, or hyphens
  - `domain` contains letters, digits, dots, and hyphens
  - `tld` (top-level domain) is at least 2 alphabetical characters
- Must handle edge cases: empty string, missing `@`, multiple `@` symbols, missing TLD
- **IMPORTANT:** Do NOT strip or trim the input string. The function receives exactly what the caller passes. If the caller passes `" user@example.com"` (leading space), return `False` — the space is part of the input.
- No external libraries — use standard `re` module only

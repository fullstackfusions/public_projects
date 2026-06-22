# URL Slug Generator

Implement `slugify(text: str) -> str` in `solution.py`.

## Requirements

- Converts any text to a URL-safe slug
- Rules (in order):
  1. Strip leading/trailing whitespace
  2. Convert to lowercase
  3. Replace spaces and underscores with hyphens
  4. Remove any character that is not a letter, digit, or hyphen
  5. Collapse multiple consecutive hyphens into a single hyphen
  6. Strip leading and trailing hyphens from the result
- Empty or whitespace-only input → return empty string `""`
- No external libraries — standard `re` module only

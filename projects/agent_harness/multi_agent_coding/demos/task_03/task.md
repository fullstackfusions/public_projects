# Run-Length Encoding

Implement two functions in `solution.py`:

```python
def encode(s: str) -> str: ...
def decode(s: str) -> str: ...
```

## Requirements

**`encode(s)`** — compresses a string using run-length encoding:
- Replace consecutive repeated characters with `<count><char>`
- If a character appears only once, output just the character (not `1a`)
- Example: `"aaabbc"` → `"3a2bc"`
- Example: `"abc"` → `"abc"` (no repetitions, no prefix)

**`decode(s)`** — reverses the encoding:
- `"3a2bc"` → `"aaabbc"`
- `"abc"` → `"abc"`
- A number prefix applies ONLY to the immediately following character

**Round-trip requirement:** `decode(encode(s)) == s` for any input string.

Handle empty strings gracefully: `encode("") == ""` and `decode("") == ""`.

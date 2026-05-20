# develop_fine_tuned_model_interface

Minimal Flask service that exposes a fine-tuned text-generation model behind a `POST /generate` endpoint.

The actual model loading lives in a sibling module called `your_model` (imported as `from your_model import generate_text`). Replace that import with your own model wrapper before running.

## Files

| File | Purpose |
|------|---------|
| `fine_tuned_model_interface.py` | Flask app with a single `/generate` route that accepts `{ "prompt": "...", "length": 50 }`. |

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python fine_tuned_model_interface.py
```

Then:

```bash
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "length": 50}'
```

## Notes

This is a thin reference template, not a complete project. You must supply your own `your_model.py` with a `generate_text(prompt, length)` function.

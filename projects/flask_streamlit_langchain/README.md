# flask_streamlit_langchain

A two-process demo that pairs:

- a **Flask REST API** backed by SQLAlchemy + Marshmallow (`Book` / `Author` models stored in a local SQLite DB), with
- a **Streamlit UI** that calls the Flask endpoints from natural-language input.

The Streamlit side is wired as a starting point for LangChain-driven query parsing (the current code does naive string matching as a placeholder).

## Files

| File | Purpose |
|------|---------|
| `flask_application.py` | Flask + SQLAlchemy + Marshmallow API exposing CRUD over `Book` / `Author`. Creates `app.db` (SQLite) on startup. Runs on `http://localhost:5000`. |
| `streamlit_ui.py` | Streamlit text input; on submit, parses commands like `update book number 4` and issues an HTTP request to the Flask API. |

## Install

```bash
pip install -r requirements.txt
```

## Run

In two separate terminals:

```bash
# Terminal 1 — API
python flask_application.py

# Terminal 2 — UI
streamlit run streamlit_ui.py
```

Then open the Streamlit URL printed in Terminal 2.

## Notes

- The `db.create_all()` call in `flask_application.py` runs at import time, which is fine for this demo but should be wrapped in an app context for production use.
- The "LangChain" reference is aspirational — extend `streamlit_ui.py` with a LangChain agent if you want true NL-to-API translation.

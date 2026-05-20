# python_websocket_and_api_calls

Three matched **server/client pairs** built with FastAPI, showing the same echo-style interaction over different transports and payload formats:

| Pair | Server | Client | What it shows |
|------|--------|--------|---------------|
| REST + WebSocket (JSON) | `rest_server.py` | `rest_client.py` | FastAPI WebSocket endpoint (`/ws/chat`) that echoes JSON messages validated with a Pydantic `TextResponse` schema. |
| XML over HTTP | `xml_server.py` | `xml_client.py` | FastAPI HTTP endpoint that accepts XML, parses with `xmltodict`, and replies in XML. |
| XML over HTTP + Pydantic validation | `xml_pydantic_server.py` | `xml_pydantic_client.py` | Same as above, but the server validates the parsed XML through a Pydantic model before responding. |

Each pair is intentionally minimal and self-contained — pick the pair that matches the transport/format you want to learn.

## Install

```bash
pip install -r requirements.txt
```

## Run

Pick one server, then run the matching client in a second terminal:

```bash
# REST / WebSocket
uvicorn rest_server:app --port 8000
python rest_client.py

# XML
uvicorn xml_server:app --port 8001
python xml_client.py

# XML + Pydantic
uvicorn xml_pydantic_server:app --port 8002
python xml_pydantic_client.py
```

Adjust the host/port inside each client if you change them on the server.

## Notes

The REST server uses a per-connection `client_id` and keeps connections in memory via a `ConnectionManager`. CORS is wide open (`allow_origins=["*"]`) for demo purposes — tighten before production use.

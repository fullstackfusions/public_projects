# mongo-orm-structure

Reference module showing how to model a **chatbot message domain** in MongoDB using:

- **`mongoengine`** for the ODM / document layer, and
- **`marshmallow-dataclass`** for typed request/response payloads (with Enums for `RequestType` / `ResponseType`).

It defines `Request` / `Response` hierarchies (`TextRequest`, `FormRequest`, `FormResponse`, etc.), an `AttachmentObject`, and the connecting glue so messages can be serialized to/from MongoDB.

## Files

| File | Purpose |
|------|---------|
| `mongo_engine_orm.py` | All model definitions, enums, and dataclasses in a single module. |

## Prerequisites

- Python 3.9+
- A running MongoDB instance on `localhost:27017`

## Install

```bash
pip install -r requirements.txt
```

## Run

This is a library-style module — import the dataclasses and `Document` subclasses from your own application:

```python
from mongo_engine_orm import TextRequest, FormRequest, AttachmentObject
```

There is no `main`/CLI entry point.

# pgvector_rag

Two-script demo of **RAG on Postgres with the `pgvector` extension**, using `langchain_postgres.PGVector` as the vector store and `OpenAIEmbeddings` for embedding.

## Files

| File | Purpose |
|------|---------|
| `create_embeddings.py` | Connects to Postgres, creates a `my_docs` collection, embeds a small set of `Document`s, and runs a sample `similarity_search`. |
| `fetch_embeddings.py` | Demonstrates a `ParentDocumentRetriever` setup that splits documents into parent/child chunks for improved retrieval. |

## Prerequisites

- Python 3.9+
- A Postgres instance with the `pgvector` extension. Easiest path is the `ankane/pgvector` Docker image:

  ```bash
  docker run --name pgvector-container \
    -e POSTGRES_USER=langchain \
    -e POSTGRES_PASSWORD=langchain \
    -e POSTGRES_DB=langchain \
    -p 6024:5432 \
    -d ankane/pgvector
  ```

- `OPENAI_API_KEY` exported in your environment.

## Install

```bash
pip install -r requirements.txt
```

## Configure

Update the `connection` string at the top of each script to match your Postgres credentials:

```python
connection = "postgresql+psycopg://langchain:langchain@localhost:6024/langchain"
```

## Run

```bash
python create_embeddings.py
python fetch_embeddings.py
```

## Notes

- `create_embeddings.py` calls `vectorstore.drop_tables()` — it wipes the collection on each run. Comment that line out if you want to keep data across runs.
- `fetch_embeddings.py` references local files `../../paul_graham_essay.txt` and `../../state_of_the_union.txt` and also imports `Chroma`; treat it as a pattern sketch — adjust paths and imports for your environment.

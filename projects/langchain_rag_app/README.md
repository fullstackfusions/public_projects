# langchain-rag-app

Minimal end-to-end **Retrieval-Augmented Generation (RAG)** example using LangChain:

1. Load a text file (`./example.txt`).
2. Split it into chunks with `RecursiveCharacterTextSplitter`.
3. Embed chunks via `OpenAIEmbeddings` and store them in a FAISS vector store.
4. Run a `ConversationalRetrievalChain` over the index and print the answer + source.

## Files

| File | Purpose |
|------|---------|
| `langchain-rag.py` | The full pipeline in a single script. |

## Prerequisites

- Python 3.9+
- An `OPENAI_API_KEY` in a `.env` file (loaded via `python-dotenv`):

  ```bash
  echo "OPENAI_API_KEY=sk-..." > .env
  ```

- An `example.txt` file in the project directory containing the source text to index.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python langchain-rag.py
```

The script prints the question, the model's answer, and the source document path.

## Notes

This uses the legacy `langchain.*` imports (`langchain.embeddings`, `langchain.vectorstores`, `langchain.chat_models`). For new projects, prefer `langchain_openai` and `langchain_community.vectorstores`.

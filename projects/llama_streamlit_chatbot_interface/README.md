# llama_streamlit_chatbot_interface

Streamlit chat UI that lets you **upload a CSV and converse with it** using a locally-hosted **Llama 2 7B chat** model (via `ctransformers`) and a FAISS vector store built from `HuggingFaceEmbeddings`.

## Files

| File | Purpose |
|------|---------|
| `streamlit_chat_interface.py` | The full Streamlit app: sidebar file uploader → builds embeddings → answers questions with `ConversationalRetrievalChain`. |
| `requirements.txt` | Python dependencies. |

## Prerequisites

- Python 3.9+
- A Llama 2 GGML model file in the project directory: `llama-2-7b-chat.ggmlv3.q8_0.bin`
  - Download from a source like Hugging Face (e.g. `TheBloke/Llama-2-7B-Chat-GGML`).

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run streamlit_chat_interface.py
```

Open the URL Streamlit prints, upload a CSV via the sidebar, then ask questions about it in the chat box.

## Notes

- Embeddings are persisted to `vectorstore/db_faiss/`.
- Generation runs entirely on CPU via `ctransformers`; expect slow responses on a small machine. Drop the model to a smaller quantization (e.g. `q4_0`) for faster inference.

"""
Ingest pipeline: PDF → text → token-aware chunks → embeddings → persisted index.

Run ONCE before any experiment. Subsequent runs load from disk in milliseconds
instead of re-embedding ~1,000 chunks every time.

Usage:
  python -m projects.local_first_reranking_layer.giant_testing.ingest
  python -m projects.local_first_reranking_layer.giant_testing.ingest --force  # re-ingest even if index exists

Output (written to giant_testing/index/):
  chunks.json      — list of chunk dicts: id, text, source, page_start, page_end
  embeddings.npy   — float32 array of shape (n_chunks, 384), L2-normalised
  manifest.json    — run stats for traceability
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import tiktoken

from projects.local_first_reranking_layer.giant_testing.config import (
    PDF_DIR, CHUNKS_FILE, EMBEDDINGS_FILE, INDEX_DIR,
    CHUNK_SIZE, CHUNK_OVERLAP, EMBED_MODEL,
)

_enc = tiktoken.get_encoding("cl100k_base")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    id: str            # "{source_stem}-p{page_start}-c{chunk_idx}"
    text: str
    source: str        # PDF filename (stem only, no extension)
    page_start: int    # 0-indexed first page this chunk touches
    page_end: int      # 0-indexed last page (inclusive)
    chunk_idx: int     # position within source


# ---------------------------------------------------------------------------
# Step 1 — PDF → per-page text blocks
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Collapse runs of whitespace; drop pure page-number lines."""
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'(?m)^\s*\d{1,4}\s*$', '', text)   # lone page numbers
    return text.strip()


def extract_pages(pdf_path: Path) -> list[dict]:
    """Return list of {page: int, text: str} dicts, skipping empty pages."""
    import fitz   # pymupdf
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = _clean(page.get_text())
        if len(text) < 40:      # skip cover images / blank pages
            continue
        pages.append({"page": i, "text": text})
    doc.close()
    return pages


# ---------------------------------------------------------------------------
# Step 2 — pages → token-aware sliding-window chunks
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[int]:
    return _enc.encode(text, disallowed_special=())


def _detokenize(ids: list[int]) -> str:
    return _enc.decode(ids)


def chunk_pages(pages: list[dict], source: str,
                chunk_size: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    """
    Concatenate all page text (tagging each with its page number), then slide a
    token window of `chunk_size` tokens with `overlap` tokens of carry-over.
    Each chunk records which pages it spans so we can cite sources.
    """
    # Build a flat token stream with page-boundary markers for metadata.
    token_stream: list[int]  = []
    page_boundaries: list[tuple[int, int]] = []   # (token_offset, page_number)

    for p in pages:
        page_boundaries.append((len(token_stream), p["page"]))
        token_stream.extend(_tokenize(p["text"]))

    def _page_at(token_offset: int) -> int:
        """Binary search: which page owns this token offset?"""
        lo, hi = 0, len(page_boundaries) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if page_boundaries[mid][0] <= token_offset:
                lo = mid
            else:
                hi = mid - 1
        return page_boundaries[lo][1]

    chunks: list[Chunk] = []
    idx = 0
    stride = chunk_size - overlap
    total = len(token_stream)

    while idx < total:
        end = min(idx + chunk_size, total)
        toks = token_stream[idx:end]
        text = _detokenize(toks).strip()
        if len(text) < 60:         # skip near-empty boundary artefacts
            idx += stride
            continue
        p_start = _page_at(idx)
        p_end   = _page_at(end - 1)
        stem    = Path(source).stem
        chunks.append(Chunk(
            id=f"{stem}-p{p_start}-c{len(chunks)}",
            text=text,
            source=stem,
            page_start=p_start,
            page_end=p_end,
            chunk_idx=len(chunks),
        ))
        idx += stride

    return chunks


# ---------------------------------------------------------------------------
# Step 3 — embed all chunks
# ---------------------------------------------------------------------------

def embed_chunks(chunks: list[Chunk], model_name: str = EMBED_MODEL) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name, device="cpu")
    texts = [c.text for c in chunks]
    print(f"  Embedding {len(texts)} chunks with {model_name} (CPU) …")
    t0 = time.perf_counter()
    embeddings = model.encode(
        texts,
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    elapsed = time.perf_counter() - t0
    print(f"  Done in {elapsed:.1f}s  shape={embeddings.shape}")
    return embeddings.astype(np.float32)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def ingest(force: bool = False) -> dict:
    if not force and CHUNKS_FILE.exists() and EMBEDDINGS_FILE.exists():
        print("Index already exists. Pass --force to re-ingest.")
        meta = json.loads((INDEX_DIR / "manifest.json").read_text())
        print(f"  {meta['total_chunks']} chunks from {len(meta['sources'])} PDFs")
        return meta

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {PDF_DIR}")

    all_chunks: list[Chunk] = []
    source_stats: list[dict] = []

    for pdf_path in pdf_files:
        print(f"\n── {pdf_path.name} ──────────────────────────")
        t0 = time.perf_counter()
        pages = extract_pages(pdf_path)
        print(f"  {len(pages)} text pages extracted")
        chunks = chunk_pages(pages, str(pdf_path.name))
        print(f"  {len(chunks)} chunks  "
              f"({CHUNK_SIZE}-tok window, {CHUNK_OVERLAP}-tok overlap)")
        total_tok = sum(len(_tokenize(c.text)) for c in chunks)
        print(f"  {total_tok:,} tokens total in this source  "
              f"(avg {total_tok // max(len(chunks), 1)} tok/chunk)")
        all_chunks.extend(chunks)
        source_stats.append({
            "file": pdf_path.name,
            "pages": len(pages),
            "chunks": len(chunks),
            "tokens": total_tok,
            "elapsed_s": round(time.perf_counter() - t0, 2),
        })

    print(f"\n── Embedding all {len(all_chunks)} chunks ──────────────────────────")
    embeddings = embed_chunks(all_chunks)

    # Persist
    print(f"\n── Saving index to {INDEX_DIR} ──────────────────────────")
    chunks_data = [asdict(c) for c in all_chunks]
    CHUNKS_FILE.write_text(json.dumps(chunks_data, indent=2))
    np.save(str(EMBEDDINGS_FILE), embeddings)

    total_tok_all = sum(s["tokens"] for s in source_stats)
    manifest = {
        "total_chunks": len(all_chunks),
        "total_tokens": total_tok_all,
        "sources": source_stats,
        "embed_model": EMBED_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
    }
    (INDEX_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\n✓ Index ready: {len(all_chunks)} chunks / {total_tok_all:,} tokens")
    for s in source_stats:
        print(f"  {s['file']}: {s['chunks']} chunks, {s['tokens']:,} tok")

    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-ingest even if index exists")
    args = ap.parse_args()
    ingest(force=args.force)

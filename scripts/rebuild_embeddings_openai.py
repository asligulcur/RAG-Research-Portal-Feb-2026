#!/usr/bin/env python3
"""
Re-embed the corpus using OpenAI text-embedding-3-small.
Use this when sentence-transformers (PyTorch) fails to load - ensures
corpus and query use the same embedding space for correct retrieval.

Requires: OPENAI_API_KEY in .env
Usage: python scripts/rebuild_embeddings_openai.py
"""

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()

# Project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EMBEDDINGS_DIR = PROJECT_ROOT / "outputs" / "embeddings"
CHUNKS_METADATA_PATH = EMBEDDINGS_DIR / "chunks_metadata.json"
BATCH_SIZE = 50  # Smaller batches for reliability; OpenAI allows up to 2048 inputs per request
EMBEDDING_DIM = 512  # text-embedding-3-small supports 512, 1024, 1536
MODEL = "text-embedding-3-small"


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set. Add it to .env and try again.")
        sys.exit(1)

    if not CHUNKS_METADATA_PATH.exists():
        print(f"ERROR: {CHUNKS_METADATA_PATH} not found. Run ingestion first.")
        sys.exit(1)

    print("Loading chunks metadata...")
    with open(CHUNKS_METADATA_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks with OpenAI {MODEL} (dim={EMBEDDING_DIM})...")

    client = OpenAI()
    all_embeddings = []

    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding batches"):
        batch = texts[i : i + BATCH_SIZE]
        for attempt in range(3):
            try:
                response = client.embeddings.create(
                    model=MODEL,
                    input=batch,
                    dimensions=EMBEDDING_DIM,
                )
                batch_embeddings = [np.array(e.embedding, dtype=np.float32) for e in response.data]
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                err_str = str(e).lower()
                if "rate limit" in err_str or "429" in err_str or "500" in err_str or "server_error" in err_str:
                    wait = 30 * (attempt + 1)
                    print(f"\nAPI error (attempt {attempt + 1}/3). Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        else:
            raise RuntimeError(f"Failed to embed batch {i} after 3 retries")
        time.sleep(0.5)  # Throttle to avoid rate limits

    embeddings = np.stack(all_embeddings).astype(np.float32)
    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    print(f"Embeddings shape: {embeddings.shape}")

    # Save
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        EMBEDDINGS_DIR / "chunk_embeddings.npz",
        embeddings=embeddings,
        chunk_ids=np.array([c["chunk_id"] for c in chunks]),
        source_ids=np.array([c["source_id"] for c in chunks]),
    )
    print(f"Saved {EMBEDDINGS_DIR / 'chunk_embeddings.npz'}")

    with open(EMBEDDINGS_DIR / "embedding_metadata.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "model": MODEL,
                "model_name": MODEL,
                "embedding_dim": EMBEDDING_DIM,
                "num_chunks": len(chunks),
                "num_papers": len(set(c["source_id"] for c in chunks)),
            },
            f,
            indent=2,
        )
    print(f"Updated embedding_metadata.json (model={MODEL}, dim={EMBEDDING_DIM})")
    print("\nDone. Restart the Streamlit app to use the new embeddings.")


if __name__ == "__main__":
    main()

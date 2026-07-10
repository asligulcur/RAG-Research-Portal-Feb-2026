# Troubleshooting

## Retrieval shows "NO EVIDENCE" for all queries

### Symptom

The portal returns "No relevant evidence found in the corpus for this query" for every question, even ones that should match (e.g., "What are the different approaches to model compression?").

### Cause

The RAG pipeline uses **sentence-transformers** for query embedding. If sentence-transformers fails to load (e.g., due to a PyTorch `libtorch_cpu.dylib` error), the system falls back to **OpenAI embeddings** for the query. The corpus was embedded with sentence-transformers, so comparing OpenAI query vectors to sentence-transformers corpus vectors produces meaningless similarity scores—everything falls below the threshold.

### Fix

1. **Reinstall PyTorch:**
   ```bash
   cd RAG-Research-Portal-Feb-2026
   source venv/bin/activate
   pip uninstall torch -y
   pip install torch
   ```

2. **Restart the Streamlit app** (or click **Reload pipeline** in the sidebar under Tools):
   ```bash
   # Stop the app (Ctrl+C), then:
   ./run_app.sh
   ```

### Fallback (if PyTorch cannot be fixed)

Re-embed the corpus with OpenAI so both corpus and query use the same embedding model:

```bash
python scripts/rebuild_embeddings_openai.py
```

Requires `OPENAI_API_KEY` in `.env`. Incurs API cost for 2,813 chunks. Takes several minutes.

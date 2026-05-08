#!/usr/bin/env python3
"""
Generate report artifacts (Evidence Table, Synthesis Memo, Annotated Bibliography)
using k=10 retrieval. Saves to report/artifacts/ for the final report.
"""
import os
import sys
import csv
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag.rag_pipeline import RAGPipeline
from app.artifacts import (
    generate_evidence_table_from_chunks,
    generate_annotated_bib_from_chunks,
    generate_synthesis_memo_with_llm,
)

QUERY = "What are the key findings about Llama small language models?"
K = 10
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "report" / "artifacts"


def main():
    print("Initializing RAG pipeline...")
    pipeline = RAGPipeline(
        embeddings_dir="outputs/embeddings",
        model="gpt-4",
    )
    print(f"Query: {QUERY}")
    print(f"Retrieving top-{K} chunks...")
    result = pipeline.query(QUERY, k=K, similarity_threshold=0.40)
    chunks = result.get("chunks", [])
    if not chunks:
        print("ERROR: No chunks retrieved")
        return 1
    print(f"Retrieved {len(chunks)} chunks")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base_name = "llama_small_models"

    # Evidence Table
    table_rows = generate_evidence_table_from_chunks(QUERY, chunks, K)
    csv_path = OUTPUT_DIR / f"{base_name}_evidence_table.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Claim", "Evidence Snippet", "Citation", "Confidence", "Notes"])
        writer.writeheader()
        writer.writerows(table_rows)
    print(f"Saved: {csv_path}")

    # Synthesis Memo
    memo_text = generate_synthesis_memo_with_llm(QUERY, chunks, K)
    memo_path = OUTPUT_DIR / f"{base_name}_synthesis_memo.md"
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write(memo_text)
    print(f"Saved: {memo_path}")

    # Annotated Bibliography
    bib_entries = generate_annotated_bib_from_chunks(QUERY, chunks, K)
    bib_path = OUTPUT_DIR / f"{base_name}_annotated_bib.md"
    with open(bib_path, "w", encoding="utf-8") as f:
        f.write("# Annotated Bibliography\n\n")
        for entry in bib_entries:
            title_line = entry.get("title_line", "")
            f.write(f"## {title_line}\n\n")
            f.write(f"**Key Claim:** {entry.get('key_claim', '')}\n")
            f.write(f"**Method:** {entry.get('method', '')}\n")
            f.write(f"**Limitations:** {entry.get('limitations', '')}\n")
            f.write(f"**Why it matters:** {entry.get('why_it_matters', '')}\n\n")
    print(f"Saved: {bib_path}")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

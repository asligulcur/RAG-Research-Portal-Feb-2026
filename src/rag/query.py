#!/usr/bin/env python3
"""
Quick query script - wrapper around rag_pipeline.py
Usage: python src/rag/query.py "your question here"
"""

import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag.rag_pipeline import RAGPipeline

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query.py \"your question here\"")
        sys.exit(1)
    
    query = sys.argv[1]
    
    pipeline = RAGPipeline(
        embeddings_dir='outputs/embeddings',
        model='gpt-3.5-turbo'
    )
    
    result = pipeline.query(query, k=10)
    print("\n" + pipeline.generator.format_response(result))

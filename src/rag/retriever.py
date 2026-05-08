"""
Retriever Module - RAG System
Retrieves top-k most relevant chunks for a given query using FAISS similarity search.
"""

import os
import json
import logging
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


class ChunkRetriever:
    """Retrieves relevant chunks using FAISS similarity search."""
    
    def __init__(
        self,
        index_path: str,
        embeddings_dir: str,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the retriever.
        
        Args:
            index_path: Path to FAISS index file
            embeddings_dir: Directory containing chunk metadata
            model_name: Name of sentence-transformers model
        """
        self.index_path = index_path
        self.embeddings_dir = embeddings_dir
        self.model_name = model_name
        
        # Load FAISS index
        logger.info(f"Loading FAISS index from: {index_path}")
        self.index = faiss.read_index(index_path)
        logger.info(f"✅ Index loaded with {self.index.ntotal} vectors")
        
        # Load chunk metadata
        metadata_path = os.path.join(embeddings_dir, "chunks_metadata.json")
        logger.info(f"Loading chunk metadata from: {metadata_path}")
        with open(metadata_path, 'r') as f:
            self.chunks_metadata = json.load(f)
        logger.info(f"✅ Loaded metadata for {len(self.chunks_metadata)} chunks")
        
        # Load embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info(f"✅ Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a query string.
        
        Args:
            query: Query text
            
        Returns:
            Query embedding (normalized)
        """
        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embedding
    
    def retrieve(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.0
    ) -> List[Dict]:
        """
        Retrieve top-k most relevant chunks for a query.
        
        Args:
            query: Query text
            k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of chunk dictionaries with metadata and similarity scores
        """
        # Embed query
        query_embedding = self.embed_query(query)
        
        # Search FAISS index
        # Note: FAISS returns distances, but with normalized vectors and IndexFlatIP,
        # distance = inner product = cosine similarity
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        # Flatten results (search returns 2D arrays)
        distances = distances[0]
        indices = indices[0]
        
        # Build result list
        results = []
        for idx, distance in zip(indices, distances):
            # Skip if below threshold
            if distance < similarity_threshold:
                continue
            
            # Get chunk metadata
            chunk_metadata = self.chunks_metadata[idx]
            
            # Add similarity score
            result = {
                **chunk_metadata,
                'similarity_score': float(distance)
            }
            results.append(result)
        
        return results
    
    def retrieve_with_context(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.0,
        add_adjacent_chunks: bool = False
    ) -> List[Dict]:
        """
        Retrieve chunks with optional adjacent chunk context.
        
        Args:
            query: Query text
            k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score
            add_adjacent_chunks: If True, include chunks before/after each result
            
        Returns:
            List of chunk dictionaries with metadata and similarity scores
        """
        results = self.retrieve(query, k, similarity_threshold)
        
        if not add_adjacent_chunks:
            return results
        
        # Note: Adjacent chunk retrieval not implemented in this version
        # Would require tracking chunk ordering in metadata (chunk_index field)
        # Current retrieval strategy (top-k with threshold) is sufficient for most queries
        return results
    
    def format_chunks_for_llm(
        self,
        chunks: List[Dict],
        include_metadata: bool = True
    ) -> str:
        """
        Format retrieved chunks for LLM context.
        
        Args:
            chunks: List of chunk dictionaries
            include_metadata: Whether to include metadata in formatting
            
        Returns:
            Formatted string for LLM context
        """
        formatted = []
        
        for i, chunk in enumerate(chunks, 1):
            chunk_text = f"[CHUNK {i}]\n"
            
            if include_metadata:
                chunk_text += f"Source ID: {chunk['source_id']}\n"
                chunk_text += f"Chunk ID: {chunk['chunk_id']}\n"
                chunk_text += f"Section: {chunk.get('section', 'Unknown')}\n"
                chunk_text += f"Similarity Score: {chunk['similarity_score']:.3f}\n"
                chunk_text += f"\n"
            
            chunk_text += f"{chunk['text']}\n"
            chunk_text += f"[/CHUNK {i}]\n"
            
            formatted.append(chunk_text)
        
        return "\n".join(formatted)


def main():
    """Test the retriever with sample queries."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test chunk retrieval")
    parser.add_argument(
        "--index-path",
        type=str,
        default="outputs/faiss_index/faiss_index.index",
        help="Path to FAISS index"
    )
    parser.add_argument(
        "--embeddings-dir",
        type=str,
        default="outputs/embeddings",
        help="Directory with chunk metadata"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Embedding model name"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What is Phi-3's performance on MMLU benchmark?",
        help="Query to test"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Number of chunks to retrieve"
    )
    
    args = parser.parse_args()
    
    # Initialize retriever
    logger.info("="*80)
    logger.info("CHUNK RETRIEVER TEST")
    logger.info("="*80)
    
    retriever = ChunkRetriever(
        index_path=args.index_path,
        embeddings_dir=args.embeddings_dir,
        model_name=args.model
    )
    
    # Test query
    logger.info(f"\nQuery: {args.query}")
    logger.info(f"Retrieving top-{args.k} chunks...")
    
    results = retriever.retrieve(args.query, k=args.k)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"RETRIEVED {len(results)} CHUNKS")
    logger.info(f"{'='*80}")
    
    for i, chunk in enumerate(results, 1):
        logger.info(f"\n--- Chunk {i} ---")
        logger.info(f"Source: {chunk['source_id']}")
        logger.info(f"Chunk ID: {chunk['chunk_id']}")
        logger.info(f"Section: {chunk.get('section', 'Unknown')}")
        logger.info(f"Similarity: {chunk['similarity_score']:.4f}")
        logger.info(f"Text preview: {chunk['text'][:200]}...")
    
    # Test formatted output
    logger.info(f"\n{'='*80}")
    logger.info("FORMATTED FOR LLM")
    logger.info(f"{'='*80}")
    formatted = retriever.format_chunks_for_llm(results[:3])
    logger.info(f"\n{formatted}")


if __name__ == "__main__":
    main()

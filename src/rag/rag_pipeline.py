"""
Complete RAG Pipeline - Retrieve and Generate
Combines retrieval and generation into one end-to-end system.

This script works around the faiss installation issue by using pre-computed embeddings
and implementing a simple cosine similarity search.
"""

import os
import json
import numpy as np
import logging
from typing import List, Dict, Optional
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import generator (package-relative for correct .llm_guard resolution)
from .generator import AnswerGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


class SimpleRetriever:
    """Simple retriever using numpy for cosine similarity (no FAISS dependency)."""
    
    def __init__(self, embeddings_dir: str):
        """
        Initialize retriever from pre-computed embeddings.
        
        Args:
            embeddings_dir: Directory containing embeddings and metadata
        """
        logger.info(f"Loading embeddings from: {embeddings_dir}")
        
        # Load embeddings
        embeddings_path = os.path.join(embeddings_dir, "chunk_embeddings.npz")
        data = np.load(embeddings_path)
        self.embeddings = data['embeddings']
        self.chunk_ids = data['chunk_ids'].tolist()
        self.source_ids = data['source_ids'].tolist()
        
        logger.info(f"✅ Loaded {len(self.embeddings)} embeddings")
        
        # Load chunk metadata
        metadata_path = os.path.join(embeddings_dir, "chunks_metadata.json")
        with open(metadata_path, 'r') as f:
            self.chunks_metadata = json.load(f)
        
        logger.info(f"✅ Loaded metadata for {len(self.chunks_metadata)} chunks")
        
        # Load embedding metadata to get model name
        embedding_meta_path = os.path.join(embeddings_dir, "embedding_metadata.json")
        with open(embedding_meta_path, 'r') as f:
            self.embedding_metadata = json.load(f)
        
        self.model_name = self.embedding_metadata.get('model', 'all-MiniLM-L6-v2')
        logger.info(f"✅ Embedding model: {self.model_name}")
        
        # Try to load sentence-transformers for query embedding
        self.encoder = None
        self.use_openai_embeddings = False
        self.embedding_dim = None  # Will be set from corpus embeddings
        
        # Get embedding dimension from corpus embeddings first
        self.embedding_dim = self.embeddings.shape[1]
        logger.info(f"Corpus embeddings dimension: {self.embedding_dim}")
        
        # Try multiple methods to load encoder
        encoder_loaded = False
        
        # Method 1: Try sentence-transformers (preferred)
        try:
            from sentence_transformers import SentenceTransformer
            # Try to use cached model first (local_files_only=True)
            # If that fails, try downloading (local_files_only=False)
            try:
                self.encoder = SentenceTransformer(self.model_name, local_files_only=True)
                logger.info("✅ Loaded sentence transformer from cache")
            except Exception:
                # If cache fails, try downloading (may fail due to network)
                self.encoder = SentenceTransformer(self.model_name, local_files_only=False)
                logger.info("✅ Downloaded sentence transformer model")
            
            actual_dim = self.encoder.get_sentence_embedding_dimension()
            if actual_dim == self.embedding_dim:
                logger.info(f"✅ Sentence transformer loaded for query embedding (dim: {actual_dim})")
                encoder_loaded = True
            else:
                logger.warning(f"Dimension mismatch: encoder={actual_dim}, corpus={self.embedding_dim}")
                self.encoder = None
        except Exception as e:
            logger.warning(f"Could not load sentence transformer: {e}")
            logger.info("Will try OpenAI embeddings API as fallback...")
        
        # Method 2: Try OpenAI embeddings API as fallback (only if sentence-transformers failed)
        if not encoder_loaded:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    from openai import OpenAI
                    self.openai_client = OpenAI(api_key=api_key)
                    self.use_openai_embeddings = True
                    logger.info(f"✅ Using OpenAI embeddings API as fallback (target dim: {self.embedding_dim})")
                    encoder_loaded = True
                else:
                    logger.warning("No OPENAI_API_KEY found. Cannot use OpenAI fallback.")
            except Exception as e2:
                logger.warning(f"Could not initialize OpenAI embeddings fallback: {e2}")
        
        if not encoder_loaded:
            logger.error(
                "⚠️  No encoder available. Query embedding will not work.\n"
                "To fix this, please run:\n"
                "  cd RAG-Research-Portal-Feb-2026\n"
                "  source venv/bin/activate\n"
                "  pip install --upgrade --force-reinstall torch sentence-transformers\n"
                "Or ensure OPENAI_API_KEY is set in your .env file."
            )
    
    def cosine_similarity(self, query_embedding: np.ndarray, k: int = 10) -> tuple:
        """
        Compute cosine similarity between query and all chunks.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of top results to return
            
        Returns:
            Tuple of (indices, scores)
        """
        # Normalize query
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # Compute dot product (cosine similarity for normalized vectors)
        scores = np.dot(self.embeddings, query_norm)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:k]
        top_scores = scores[top_indices]
        
        return top_indices, top_scores
    
    def retrieve(
        self, 
        query: str, 
        k: int = 10,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        authors: Optional[List[str]] = None,
        source_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Retrieve top-k chunks for a query with optional metadata filtering.
        
        ENHANCEMENT: Metadata filtering (year/author/type) and faceted retrieval
        
        Args:
            query: Query string
            k: Number of chunks to retrieve
            year_min: Minimum publication year (inclusive)
            year_max: Maximum publication year (inclusive)
            authors: List of author names to filter by (any match)
            source_types: List of source types (e.g., ["conference", "journal"])
            
        Returns:
            List of chunk dictionaries with similarity scores
        """
        # Embed query
        logger.info(f"Embedding query: {query[:100]}...")
        
        if self.encoder is not None:
            # Use sentence-transformers
            query_embedding = self.encoder.encode([query], normalize_embeddings=True)[0]
        elif self.use_openai_embeddings:
            # Use OpenAI embeddings API as fallback
            try:
                # OpenAI text-embedding-3-small supports: 512, 1024, 1536
                # Our corpus uses 384 dimensions (all-MiniLM-L6-v2)
                # We'll use 512 and truncate/pad to match
                if self.embedding_dim == 384:
                    # Use 512 and truncate to 384
                    model_name = "text-embedding-3-small"
                    dimensions = 512
                    truncate = True
                elif self.embedding_dim == 1536:
                    model_name = "text-embedding-ada-002"
                    dimensions = None
                    truncate = False
                else:
                    # Try to use closest supported dimension
                    supported_dims = [512, 1024, 1536]
                    closest_dim = min(supported_dims, key=lambda x: abs(x - self.embedding_dim))
                    model_name = "text-embedding-3-small"
                    dimensions = closest_dim
                    truncate = (closest_dim != self.embedding_dim)
                
                # Create embedding request
                params = {
                    "model": model_name,
                    "input": query
                }
                if dimensions is not None:
                    params["dimensions"] = dimensions
                
                response = self.openai_client.embeddings.create(**params)
                query_embedding = np.array(response.data[0].embedding)
                
                # Truncate or pad if needed to match corpus dimension
                if truncate and len(query_embedding) > self.embedding_dim:
                    query_embedding = query_embedding[:self.embedding_dim]
                    logger.info(f"Truncated embedding from {len(response.data[0].embedding)} to {self.embedding_dim} dimensions")
                elif len(query_embedding) < self.embedding_dim:
                    # Pad with zeros (shouldn't happen with OpenAI, but just in case)
                    padding = np.zeros(self.embedding_dim - len(query_embedding))
                    query_embedding = np.concatenate([query_embedding, padding])
                    logger.warning(f"Padded embedding from {len(response.data[0].embedding)} to {self.embedding_dim} dimensions")
                
                # Verify dimension matches
                if len(query_embedding) != self.embedding_dim:
                    raise ValueError(
                        f"Embedding dimension mismatch: got {len(query_embedding)}, "
                        f"expected {self.embedding_dim}. Cannot perform similarity search."
                    )
                
                # Normalize for cosine similarity
                query_embedding = query_embedding / np.linalg.norm(query_embedding)
                logger.info(f"✅ Query embedded using OpenAI API (dim: {len(query_embedding)})")
            except Exception as e:
                error_msg = str(e)
                if "Connection" in error_msg or "connection" in error_msg:
                    raise RuntimeError(
                        f"Failed to connect to OpenAI API: {error_msg}\n\n"
                        "Possible solutions:\n"
                        "1. Check your internet connection\n"
                        "2. Verify OPENAI_API_KEY in .env file is correct\n"
                        "3. Check firewall/proxy settings\n"
                        "4. Fix PyTorch installation (see FIX_EMBEDDINGS.md)"
                    )
                else:
                    raise RuntimeError(f"Failed to embed query using OpenAI API: {e}")
        else:
            raise RuntimeError(
                "No encoder available. Cannot embed query.\n"
                "Please either:\n"
                "1. Fix PyTorch/sentence-transformers installation, or\n"
                "2. Set OPENAI_API_KEY environment variable for fallback embeddings"
            )
        
        # Apply metadata filtering BEFORE retrieval if filters provided
        filtered_indices = None
        if any([year_min, year_max, authors, source_types]):
            logger.info("Applying metadata filters...")
            filtered_indices = self._apply_metadata_filters(
                year_min, year_max, authors, source_types
            )
            logger.info(f"  → {len(filtered_indices)} chunks pass filters (from {len(self.chunks_metadata)} total)")
        
        # Search (filtered or full)
        if filtered_indices is not None:
            # Search only within filtered chunks
            indices, scores = self._filtered_cosine_similarity(
                query_embedding, filtered_indices, k=k
            )
        else:
            # Search all chunks
            indices, scores = self.cosine_similarity(query_embedding, k=k)
        
        # Build results
        results = []
        for idx, score in zip(indices, scores):
            chunk = self.chunks_metadata[idx].copy()
            chunk['similarity_score'] = float(score)
            results.append(chunk)
        
        return results
    
    def _apply_metadata_filters(
        self,
        year_min: Optional[int],
        year_max: Optional[int],
        authors: Optional[List[str]],
        source_types: Optional[List[str]]
    ) -> List[int]:
        """
        Apply metadata filters to get valid chunk indices.
        
        Args:
            year_min: Minimum year
            year_max: Maximum year
            authors: List of author names
            source_types: List of source types
            
        Returns:
            List of chunk indices that pass all filters
        """
        valid_indices = []
        
        for idx, chunk in enumerate(self.chunks_metadata):
            # Get metadata (could be 'paper_metadata' or 'metadata')
            metadata = chunk.get('paper_metadata', chunk.get('metadata', {}))
            
            # Year filter
            if year_min is not None or year_max is not None:
                year_str = metadata.get('year')
                if year_str is None:
                    continue
                try:
                    year = int(year_str)
                except (ValueError, TypeError):
                    continue
                if year_min and year < year_min:
                    continue
                if year_max and year > year_max:
                    continue
            
            # Author filter (match if any author in list appears in paper authors)
            if authors:
                paper_authors = metadata.get('authors', '').lower()
                if not any(author.lower() in paper_authors for author in authors):
                    continue
            
            # Source type filter
            if source_types:
                source_type = metadata.get('source_type', '').lower()
                if source_type not in [st.lower() for st in source_types]:
                    continue
            
            valid_indices.append(idx)
        
        return valid_indices
    
    def _filtered_cosine_similarity(
        self, 
        query_embedding: np.ndarray, 
        valid_indices: List[int],
        k: int = 10
    ) -> tuple:
        """
        Compute cosine similarity only for filtered chunks.
        
        Args:
            query_embedding: Query embedding vector
            valid_indices: List of valid chunk indices
            k: Number of top results to return
            
        Returns:
            Tuple of (indices, scores)
        """
        if len(valid_indices) == 0:
            logger.warning("No chunks pass filters!")
            return np.array([]), np.array([])
        
        # Get embeddings for valid chunks only
        filtered_embeddings = self.embeddings[valid_indices]
        
        # Normalize query
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # Compute dot product
        scores = np.dot(filtered_embeddings, query_norm)
        
        # Get top-k from filtered set
        k_actual = min(k, len(scores))
        top_positions = np.argsort(scores)[::-1][:k_actual]
        
        # Map back to original indices
        top_indices = np.array([valid_indices[pos] for pos in top_positions])
        top_scores = scores[top_positions]
        
        return top_indices, top_scores


class RAGPipeline:
    """End-to-end RAG pipeline combining retrieval and generation."""
    
    def __init__(
        self,
        embeddings_dir: str = "outputs/embeddings",
        model: str = "gpt-4",
        api_key: Optional[str] = None
    ):
        """
        Initialize RAG pipeline.
        
        Args:
            embeddings_dir: Directory with embeddings and metadata
            model: LLM model name
            api_key: OpenAI API key
        """
        logger.info("="*80)
        logger.info("INITIALIZING RAG PIPELINE")
        logger.info("="*80)
        
        # Initialize retriever
        self.retriever = SimpleRetriever(embeddings_dir)
        
        # Initialize generator
        self.generator = AnswerGenerator(api_key=api_key, model=model)
        
        logger.info("="*80)
        logger.info("✅ RAG PIPELINE READY")
        logger.info("="*80)
    
    def query(
        self,
        question: str,
        k: int = 10,
        similarity_threshold: float = 0.40,
        system_prompt: Optional[str] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        authors: Optional[List[str]] = None,
        source_types: Optional[List[str]] = None
    ) -> Dict:
        """
        Answer a question using RAG.
        
        ENHANCEMENT: Supports metadata filtering (year/author/type)
        
        Args:
            question: User question
            k: Number of chunks to retrieve
            similarity_threshold: Minimum chunk similarity score to keep
            system_prompt: Optional custom system prompt
            year_min: Filter by minimum publication year
            year_max: Filter by maximum publication year
            authors: Filter by author names (list)
            source_types: Filter by source types (list)
            
        Returns:
            Dictionary with answer, citations, chunks, and metadata
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"QUERY: {question}")
        if year_min or year_max or authors or source_types:
            logger.info("FILTERS:")
            if year_min or year_max:
                logger.info(f"  • Year: {year_min or 'any'} - {year_max or 'any'}")
            if authors:
                logger.info(f"  • Authors: {authors}")
            if source_types:
                logger.info(f"  • Types: {source_types}")
        logger.info(f"{'='*80}")
        
        # Step 1: Retrieve relevant chunks (with optional filtering)
        logger.info(f"Retrieving top-{k} chunks...")
        chunks = self.retriever.retrieve(
            question, 
            k=k,
            year_min=year_min,
            year_max=year_max,
            authors=authors,
            source_types=source_types
        )
        
        # TRUST BEHAVIOR FIX: Filter out low-quality retrievals
        # Default remains 0.40; caller can override for controlled fallback retrieval.
        chunks_before_filter = len(chunks)
        chunks = [c for c in chunks if c['similarity_score'] >= similarity_threshold]
        
        if chunks_before_filter > len(chunks):
            logger.warning(
                f"⚠️  Filtered out {chunks_before_filter - len(chunks)} low-quality chunks "
                f"(similarity < {similarity_threshold})"
            )
        
        logger.info(f"✅ Retrieved {len(chunks)} chunks")
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"  {i}. {chunk['source_id']} / {chunk['chunk_id']} (score: {chunk['similarity_score']:.3f})")
        
        # Step 2: Generate answer
        logger.info(f"\nGenerating answer...")
        result = self.generator.generate(question, chunks, system_prompt)

        # Add retrieval diagnostics for transparency and downstream UI.
        result.setdefault("metadata", {})
        result["metadata"]["similarity_threshold"] = similarity_threshold
        result["metadata"]["chunks_before_filter"] = chunks_before_filter
        result["metadata"]["chunks_after_filter"] = len(chunks)
        result["metadata"]["k"] = k
        
        return result
    
    def interactive_mode(self):
        """Run in interactive query mode."""
        print("\n" + "="*80)
        print("RAG PIPELINE - INTERACTIVE MODE")
        print("="*80)
        print("Enter your questions (or 'quit' to exit)")
        print("="*80 + "\n")
        
        while True:
            try:
                question = input("\nQuestion: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if not question:
                    continue
                
                # Query the system
                result = self.query(question, k=10)
                
                # Display result
                print("\n" + self.generator.format_response(result))
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                continue


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Pipeline - Retrieve and Generate answers from research papers"
    )
    parser.add_argument(
        "--embeddings-dir",
        type=str,
        default="outputs/embeddings",
        help="Directory with embeddings and metadata"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4",
        help="LLM model name (gpt-4, gpt-3.5-turbo, etc.)"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to run (otherwise starts interactive mode)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Number of chunks to retrieve"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = RAGPipeline(
        embeddings_dir=args.embeddings_dir,
        model=args.model
    )
    
    # Run query or interactive mode
    if args.query:
        # Single query mode
        result = pipeline.query(args.query, k=args.k)
        print("\n" + pipeline.generator.format_response(result))
    else:
        # Interactive mode
        pipeline.interactive_mode()


if __name__ == "__main__":
    main()

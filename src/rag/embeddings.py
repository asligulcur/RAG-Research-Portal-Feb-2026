"""
Chunk Embeddings Generator
Creates dense vector embeddings for text chunks using sentence-transformers.
"""

import json
from pathlib import Path
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChunkEmbedder:
    """
    Generate embeddings for text chunks using sentence-transformers.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedder with pre-trained model.
        
        Args:
            model_name: Sentence-transformers model name
                - 'all-MiniLM-L6-v2': Fast, 384 dims (default)
                - 'all-mpnet-base-v2': Better quality, 768 dims
                - 'multi-qa-mpnet-base-dot-v1': Optimized for Q&A
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
    
    def embed_texts(self, texts: List[str], batch_size: int = 32, show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once
            show_progress: Whether to show progress bar
            
        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        return embeddings
    
    def embed_single(self, text: str) -> np.ndarray:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            1D numpy array of shape (embedding_dim,)
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding


def load_all_chunks(processed_dir: str = "data/processed") -> List[Dict]:
    """
    Load all chunks from processed JSON files.
    
    Args:
        processed_dir: Directory containing processed JSON files
        
    Returns:
        List of chunk dictionaries with metadata
    """
    processed_path = Path(processed_dir)
    
    if not processed_path.exists():
        raise FileNotFoundError(f"Processed directory not found: {processed_dir}")
    
    all_chunks = []
    json_files = sorted(processed_path.glob("*.json"))
    
    logger.info(f"Loading chunks from {len(json_files)} files...")
    
    for json_file in tqdm(json_files, desc="Loading papers"):
        with open(json_file, 'r', encoding='utf-8') as f:
            paper_data = json.load(f)
            
            # Add paper-level metadata to each chunk
            for chunk in paper_data['chunks']:
                chunk['paper_metadata'] = paper_data['metadata']
                all_chunks.append(chunk)
    
    logger.info(f"Loaded {len(all_chunks)} chunks total")
    return all_chunks


def create_chunk_embeddings(
    processed_dir: str = "data/processed",
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
    output_path: str = "outputs/embeddings"
) -> Dict:
    """
    Create embeddings for all chunks and save to disk.
    
    Args:
        processed_dir: Directory with processed JSON files
        model_name: Sentence-transformers model name
        batch_size: Batch size for embedding generation
        output_path: Where to save embeddings
        
    Returns:
        Dict with embeddings, chunks, and metadata
    """
    # Create output directory
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load all chunks
    chunks = load_all_chunks(processed_dir)
    
    # Extract text for embedding
    texts = [chunk['text'] for chunk in chunks]
    
    # Initialize embedder
    embedder = ChunkEmbedder(model_name)
    
    # Generate embeddings
    logger.info(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = embedder.embed_texts(texts, batch_size=batch_size)
    
    logger.info(f"Embeddings shape: {embeddings.shape}")
    
    # Save embeddings and chunks
    embedding_data = {
        'embeddings': embeddings,
        'chunks': chunks,
        'metadata': {
            'model_name': model_name,
            'embedding_dim': embedder.embedding_dim,
            'num_chunks': len(chunks),
            'num_papers': len(set(c['source_id'] for c in chunks))
        }
    }
    
    # Save as numpy archive
    embeddings_file = output_dir / "chunk_embeddings.npz"
    np.savez_compressed(
        embeddings_file,
        embeddings=embeddings,
        chunk_ids=np.array([c['chunk_id'] for c in chunks]),
        source_ids=np.array([c['source_id'] for c in chunks])
    )
    logger.info(f"✅ Embeddings saved to: {embeddings_file}")
    
    # Save chunks as JSON for reference
    chunks_file = output_dir / "chunks_metadata.json"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2)
    logger.info(f"✅ Chunk metadata saved to: {chunks_file}")
    
    # Save embedding metadata
    metadata_file = output_dir / "embedding_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(embedding_data['metadata'], f, indent=2)
    logger.info(f"✅ Metadata saved to: {metadata_file}")
    
    return embedding_data


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate chunk embeddings')
    parser.add_argument(
        '--model',
        default='all-MiniLM-L6-v2',
        choices=['all-MiniLM-L6-v2', 'all-mpnet-base-v2', 'multi-qa-mpnet-base-dot-v1'],
        help='Sentence-transformers model to use'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for embedding generation'
    )
    parser.add_argument(
        '--output',
        default='outputs/embeddings',
        help='Output directory for embeddings'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("CHUNK EMBEDDING GENERATION")
    logger.info("=" * 80)
    
    embedding_data = create_chunk_embeddings(
        model_name=args.model,
        batch_size=args.batch_size,
        output_path=args.output
    )
    
    logger.info("\n" + "=" * 80)
    logger.info("EMBEDDING GENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Model: {embedding_data['metadata']['model_name']}")
    logger.info(f"Embedding dimension: {embedding_data['metadata']['embedding_dim']}")
    logger.info(f"Total chunks: {embedding_data['metadata']['num_chunks']}")
    logger.info(f"Total papers: {embedding_data['metadata']['num_papers']}")
    logger.info(f"Output: {args.output}/")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

"""
FAISS Vector Index Builder
Builds and saves a FAISS index for fast similarity search.
"""

import json
import numpy as np
import faiss
from pathlib import Path
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FAISSIndexBuilder:
    """
    Build and manage FAISS index for chunk embeddings.
    """
    
    def __init__(self, embedding_dim: int):
        """
        Initialize index builder.
        
        Args:
            embedding_dim: Dimension of embedding vectors
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.index_type = None
    
    def build_flat_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build a flat (exact) index with inner product similarity.
        Best for small-medium datasets (<1M vectors).
        
        Args:
            embeddings: numpy array of shape (n_chunks, embedding_dim)
            
        Returns:
            FAISS index
        """
        logger.info(f"Building Flat index (exact search)...")
        
        # Use inner product for normalized vectors (equivalent to cosine similarity)
        index = faiss.IndexFlatIP(self.embedding_dim)
        
        # Add vectors to index
        index.add(embeddings.astype('float32'))
        
        logger.info(f"✅ Index built with {index.ntotal} vectors")
        
        self.index = index
        self.index_type = "Flat"
        return index
    
    def build_ivf_index(
        self,
        embeddings: np.ndarray,
        nlist: int = 100,
        nprobe: int = 10
    ) -> faiss.Index:
        """
        Build an IVF index for faster approximate search.
        Good for large datasets (>100k vectors).
        
        Args:
            embeddings: numpy array of shape (n_chunks, embedding_dim)
            nlist: Number of clusters (more = faster but less accurate)
            nprobe: Number of clusters to search (more = slower but more accurate)
            
        Returns:
            FAISS index
        """
        logger.info(f"Building IVF index (approximate search)...")
        logger.info(f"  nlist={nlist}, nprobe={nprobe}")
        
        # Create quantizer and IVF index
        quantizer = faiss.IndexFlatIP(self.embedding_dim)
        index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, nlist)
        
        # Train index on embeddings
        logger.info("Training index...")
        index.train(embeddings.astype('float32'))
        
        # Add vectors
        logger.info("Adding vectors to index...")
        index.add(embeddings.astype('float32'))
        
        # Set search parameters
        index.nprobe = nprobe
        
        logger.info(f"✅ Index built with {index.ntotal} vectors")
        
        self.index = index
        self.index_type = f"IVF{nlist}"
        return index
    
    def save_index(self, output_dir: str, index_name: str = "faiss_index"):
        """
        Save FAISS index to disk.
        
        Args:
            output_dir: Directory to save index
            index_name: Base name for index file
        """
        if self.index is None:
            raise ValueError("No index to save. Build index first.")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        index_file = output_path / f"{index_name}.index"
        faiss.write_index(self.index, str(index_file))
        
        logger.info(f"✅ Index saved to: {index_file}")
        
        # Save index metadata
        metadata = {
            'index_type': self.index_type,
            'embedding_dim': self.embedding_dim,
            'num_vectors': self.index.ntotal
        }
        
        metadata_file = output_path / f"{index_name}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Index metadata saved to: {metadata_file}")
        
        return index_file
    
    @staticmethod
    def load_index(index_path: str) -> faiss.Index:
        """
        Load a FAISS index from disk.
        
        Args:
            index_path: Path to index file
            
        Returns:
            FAISS index
        """
        logger.info(f"Loading index from: {index_path}")
        index = faiss.read_index(index_path)
        logger.info(f"✅ Loaded index with {index.ntotal} vectors")
        return index


def build_and_save_index(
    embeddings_dir: str = "outputs/embeddings",
    output_dir: str = "outputs/faiss_index",
    index_type: str = "flat",
    nlist: int = 100,
    nprobe: int = 10
) -> str:
    """
    Build FAISS index from embeddings and save to disk.
    
    Args:
        embeddings_dir: Directory containing chunk_embeddings.npz
        output_dir: Directory to save FAISS index
        index_type: 'flat' (exact) or 'ivf' (approximate)
        nlist: For IVF index, number of clusters
        nprobe: For IVF index, number of clusters to search
        
    Returns:
        Path to saved index file
    """
    # Load embeddings
    embeddings_file = Path(embeddings_dir) / "chunk_embeddings.npz"
    
    if not embeddings_file.exists():
        raise FileNotFoundError(
            f"Embeddings not found: {embeddings_file}\n"
            "Run src/rag/embeddings.py first to generate embeddings."
        )
    
    logger.info(f"Loading embeddings from: {embeddings_file}")
    data = np.load(embeddings_file)
    embeddings = data['embeddings']
    
    logger.info(f"Loaded embeddings: shape={embeddings.shape}")
    
    # Load metadata
    metadata_file = Path(embeddings_dir) / "embedding_metadata.json"
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    embedding_dim = metadata['embedding_dim']
    
    # Build index
    builder = FAISSIndexBuilder(embedding_dim)
    
    if index_type == "flat":
        builder.build_flat_index(embeddings)
    elif index_type == "ivf":
        builder.build_ivf_index(embeddings, nlist=nlist, nprobe=nprobe)
    else:
        raise ValueError(f"Unknown index type: {index_type}. Use 'flat' or 'ivf'.")
    
    # Save index
    index_path = builder.save_index(output_dir)
    
    return str(index_path)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build FAISS index from embeddings')
    parser.add_argument(
        '--embeddings-dir',
        default='outputs/embeddings',
        help='Directory containing chunk embeddings'
    )
    parser.add_argument(
        '--output-dir',
        default='outputs/faiss_index',
        help='Output directory for FAISS index'
    )
    parser.add_argument(
        '--index-type',
        default='flat',
        choices=['flat', 'ivf'],
        help='Index type: flat (exact) or ivf (approximate)'
    )
    parser.add_argument(
        '--nlist',
        type=int,
        default=100,
        help='For IVF index: number of clusters'
    )
    parser.add_argument(
        '--nprobe',
        type=int,
        default=10,
        help='For IVF index: number of clusters to search'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("FAISS INDEX BUILDER")
    logger.info("=" * 80)
    
    index_path = build_and_save_index(
        embeddings_dir=args.embeddings_dir,
        output_dir=args.output_dir,
        index_type=args.index_type,
        nlist=args.nlist,
        nprobe=args.nprobe
    )
    
    logger.info("\n" + "=" * 80)
    logger.info("INDEX BUILD COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Index saved to: {index_path}")
    logger.info(f"Index type: {args.index_type}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

"""
Main Ingestion Pipeline
Orchestrates PDF parsing, chunking, and JSON output for entire corpus.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List
import logging
from datetime import datetime

from pdf_parser import parse_single_pdf
from chunker import create_chunks_from_parsed_pdf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Complete ingestion pipeline for research paper corpus.
    """
    
    def __init__(
        self,
        manifest_path: str = "data/data_manifest.csv",
        raw_dir: str = "data/raw",
        processed_dir: str = "data/processed",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize ingestion pipeline.
        
        Args:
            manifest_path: Path to data manifest CSV
            raw_dir: Directory containing raw PDFs
            processed_dir: Directory for processed JSON output
            chunk_size: Target characters per chunk
            chunk_overlap: Overlapping characters between chunks
        """
        self.manifest_path = Path(manifest_path)
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create output directory if needed
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'total_papers': 0,
            'successfully_processed': 0,
            'failed': 0,
            'total_chunks': 0,
            'total_pages': 0,
            'errors': []
        }
    
    def load_manifest(self) -> List[Dict]:
        """
        Load corpus manifest.
        
        Returns:
            List of paper metadata dictionaries
        """
        papers = []
        
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                papers.append(row)
        
        logger.info(f"Loaded {len(papers)} papers from manifest")
        return papers
    
    def process_single_paper(
        self,
        paper_metadata: Dict,
        pdf_method: str = 'pypdf2'
    ) -> Dict:
        """
        Process a single paper: parse PDF and create chunks.
        
        Args:
            paper_metadata: Dict from manifest with source_id, raw_path, etc.
            pdf_method: 'pypdf2' (fast) or 'pdfplumber' (accurate)
            
        Returns:
            Dict with paper metadata, chunks, and statistics
        """
        source_id = paper_metadata['source_id']
        raw_path = paper_metadata['raw_path']
        
        logger.info(f"Processing {source_id}: {raw_path}")
        
        try:
            # Step 1: Parse PDF
            parsed_pdf = parse_single_pdf(raw_path, method=pdf_method)
            
            # Step 2: Create chunks
            chunks = create_chunks_from_parsed_pdf(
                parsed_pdf,
                source_id=source_id,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                section_aware=True
            )
            
            # Step 3: Compile output
            output = {
                'source_id': source_id,
                'metadata': {
                    'title': paper_metadata.get('title', ''),
                    'authors': paper_metadata.get('authors', ''),
                    'year': paper_metadata.get('year', ''),
                    'venue': paper_metadata.get('venue', ''),
                    'url': paper_metadata.get('url_or_doi', ''),
                    'source_type': paper_metadata.get('source_type', ''),
                    'relevance_note': paper_metadata.get('relevance_note', '')
                },
                'pdf_metadata': parsed_pdf['metadata'],
                'statistics': {
                    'total_pages': parsed_pdf['total_pages'],
                    'total_chunks': len(chunks),
                    'avg_chunk_size': sum(c['char_count'] for c in chunks) / len(chunks) if chunks else 0,
                    'ingestion_timestamp': datetime.now().isoformat()
                },
                'chunks': chunks
            }
            
            self.stats['total_pages'] += parsed_pdf['total_pages']
            self.stats['total_chunks'] += len(chunks)
            self.stats['successfully_processed'] += 1
            
            logger.info(f"  ✅ Created {len(chunks)} chunks from {parsed_pdf['total_pages']} pages")
            
            return output
            
        except Exception as e:
            logger.error(f"  ❌ Failed to process {source_id}: {e}")
            self.stats['failed'] += 1
            self.stats['errors'].append({
                'source_id': source_id,
                'error': str(e)
            })
            return None
    
    def save_processed_paper(self, processed_data: Dict):
        """
        Save processed paper data to JSON.
        
        Args:
            processed_data: Output from process_single_paper()
        """
        if not processed_data:
            return
        
        source_id = processed_data['source_id']
        output_path = self.processed_dir / f"{source_id}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  💾 Saved to {output_path}")
    
    def run(self, limit: int = None, pdf_method: str = 'pypdf2'):
        """
        Run complete ingestion pipeline on all papers.
        
        Args:
            limit: Optional limit on number of papers to process (for testing)
            pdf_method: 'pypdf2' or 'pdfplumber'
        """
        logger.info("=" * 80)
        logger.info("Starting Ingestion Pipeline")
        logger.info("=" * 80)
        
        # Load manifest
        papers = self.load_manifest()
        self.stats['total_papers'] = len(papers)
        
        if limit:
            papers = papers[:limit]
            logger.info(f"⚠️  Limiting to first {limit} papers for testing")
        
        logger.info(f"\nProcessing {len(papers)} papers...")
        logger.info(f"Chunk size: {self.chunk_size} chars, overlap: {self.chunk_overlap} chars")
        logger.info(f"PDF method: {pdf_method}")
        logger.info("")
        
        # Process each paper
        for idx, paper in enumerate(papers, start=1):
            logger.info(f"\n[{idx}/{len(papers)}] {paper['source_id']}")
            
            processed_data = self.process_single_paper(paper, pdf_method=pdf_method)
            
            if processed_data:
                self.save_processed_paper(processed_data)
        
        # Final report
        self.print_summary()
        self.save_ingestion_log()
    
    def print_summary(self):
        """Print ingestion statistics."""
        logger.info("\n" + "=" * 80)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total papers in manifest: {self.stats['total_papers']}")
        logger.info(f"Successfully processed:    {self.stats['successfully_processed']}")
        logger.info(f"Failed:                    {self.stats['failed']}")
        logger.info(f"Total pages extracted:     {self.stats['total_pages']}")
        logger.info(f"Total chunks created:      {self.stats['total_chunks']}")
        
        if self.stats['successfully_processed'] > 0:
            avg_chunks = self.stats['total_chunks'] / self.stats['successfully_processed']
            avg_pages = self.stats['total_pages'] / self.stats['successfully_processed']
            logger.info(f"Average chunks per paper:  {avg_chunks:.1f}")
            logger.info(f"Average pages per paper:   {avg_pages:.1f}")
        
        if self.stats['errors']:
            logger.info(f"\n⚠️  Errors encountered:")
            for error in self.stats['errors']:
                logger.info(f"  - {error['source_id']}: {error['error']}")
        
        logger.info("\n✅ Processed files saved to: " + str(self.processed_dir))
        logger.info("=" * 80)
    
    def save_ingestion_log(self):
        """Save ingestion statistics to log file."""
        log_path = Path("logs/ingestion_log.json")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap,
                'manifest_path': str(self.manifest_path),
                'raw_dir': str(self.raw_dir),
                'processed_dir': str(self.processed_dir)
            },
            'statistics': self.stats
        }
        
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"📊 Ingestion log saved to: {log_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest research paper corpus')
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of papers to process (for testing)'
    )
    parser.add_argument(
        '--method',
        choices=['pypdf2', 'pdfplumber'],
        default='pypdf2',
        help='PDF extraction method (pypdf2=fast, pdfplumber=accurate)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1000,
        help='Target characters per chunk'
    )
    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=200,
        help='Overlapping characters between chunks'
    )
    
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = IngestionPipeline(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    pipeline.run(limit=args.limit, pdf_method=args.method)


if __name__ == "__main__":
    main()

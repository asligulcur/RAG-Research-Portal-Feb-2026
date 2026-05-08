"""
Text Chunking with Section Awareness
Creates citation-traceable chunks from parsed PDFs.
"""

import re
from typing import Dict, List, Optional
import hashlib


class TextChunker:
    """
    Create overlapping chunks from text with section awareness.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        section_aware: bool = True
    ):
        """
        Initialize chunker with strategy parameters.
        
        Args:
            chunk_size: Target characters per chunk
            chunk_overlap: Overlapping characters between chunks
            section_aware: Whether to respect section boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.section_aware = section_aware
        
        # Common academic section headers
        self.section_patterns = [
            r'^abstract\s*$',
            r'^\d+\.?\s+(introduction|background|related work|motivation)',
            r'^\d+\.?\s+(method|methodology|approach|framework)',
            r'^\d+\.?\s+(experiment|evaluation|results)',
            r'^\d+\.?\s+(discussion|analysis)',
            r'^\d+\.?\s+(conclusion|future work)',
            r'^references\s*$',
            r'^appendix',
        ]
    
    def detect_section_boundaries(self, text: str) -> List[Dict]:
        """
        Detect section headers and their positions in text.
        
        Args:
            text: Full document text
            
        Returns:
            List of dicts with section_name, start_pos, and header text
        """
        sections = []
        lines = text.split('\n')
        current_pos = 0
        
        for line_idx, line in enumerate(lines):
            line_lower = line.strip().lower()
            
            # Check if line matches any section pattern
            for pattern in self.section_patterns:
                if re.match(pattern, line_lower, re.IGNORECASE):
                    sections.append({
                        'section_name': line.strip(),
                        'start_pos': current_pos,
                        'line_num': line_idx
                    })
                    break
            
            current_pos += len(line) + 1  # +1 for newline
        
        return sections
    
    def chunk_by_section(
        self,
        text: str,
        source_id: str,
        page_info: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Create chunks respecting section boundaries.
        
        Args:
            text: Full document text
            source_id: Source identifier for citations
            page_info: Optional list of page dictionaries with page_num and text
            
        Returns:
            List of chunk dictionaries
        """
        sections = self.detect_section_boundaries(text)
        
        if not sections:
            # No sections detected, fall back to simple chunking
            return self.chunk_simple(text, source_id, page_info)
        
        chunks = []
        chunk_counter = 0
        
        # Add implicit first section (before first detected section)
        if sections[0]['start_pos'] > 0:
            sections.insert(0, {
                'section_name': 'Header/Title',
                'start_pos': 0,
                'line_num': 0
            })
        
        # Process each section
        for idx, section in enumerate(sections):
            section_start = section['start_pos']
            
            # Determine section end (start of next section or end of text)
            if idx + 1 < len(sections):
                section_end = sections[idx + 1]['start_pos']
            else:
                section_end = len(text)
            
            section_text = text[section_start:section_end].strip()
            
            # Skip very short sections
            if len(section_text) < 100:
                continue
            
            # Chunk this section
            section_chunks = self._chunk_text_with_overlap(
                section_text,
                section_name=section['section_name']
            )
            
            # Create chunk objects
            for chunk_text in section_chunks:
                chunk_id = f"{source_id}_chunk_{chunk_counter:04d}"
                
                chunks.append({
                    'chunk_id': chunk_id,
                    'source_id': source_id,
                    'text': chunk_text,
                    'section': section['section_name'],
                    'char_count': len(chunk_text),
                    'chunk_index': chunk_counter
                })
                
                chunk_counter += 1
        
        return chunks
    
    def chunk_simple(
        self,
        text: str,
        source_id: str,
        page_info: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Create simple overlapping chunks without section awareness.
        
        Args:
            text: Full document text
            source_id: Source identifier
            page_info: Optional page information
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        chunk_texts = self._chunk_text_with_overlap(text)
        
        for idx, chunk_text in enumerate(chunk_texts):
            chunk_id = f"{source_id}_chunk_{idx:04d}"
            
            chunks.append({
                'chunk_id': chunk_id,
                'source_id': source_id,
                'text': chunk_text,
                'section': 'unknown',
                'char_count': len(chunk_text),
                'chunk_index': idx
            })
        
        return chunks
    
    def _chunk_text_with_overlap(
        self,
        text: str,
        section_name: str = 'unknown'
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            section_name: Name of section (for context)
            
        Returns:
            List of chunk strings
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If not at the end, try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending in the overlap zone
                search_start = max(start, end - 200)
                search_text = text[search_start:end + 200]
                
                # Find last sentence boundary
                sentence_end = max(
                    search_text.rfind('. '),
                    search_text.rfind('.\n'),
                    search_text.rfind('! '),
                    search_text.rfind('? ')
                )
                
                if sentence_end != -1:
                    # Adjust end to sentence boundary
                    end = search_start + sentence_end + 1
            
            chunk = text[start:end].strip()
            
            if chunk:
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start <= 0 and len(chunks) > 0:
                break
        
        return chunks
    
    def add_page_numbers(
        self,
        chunks: List[Dict],
        page_info: List[Dict]
    ) -> List[Dict]:
        """
        Add page number information to chunks.
        
        Args:
            chunks: List of chunk dictionaries
            page_info: List of page dictionaries with page_num and text
            
        Returns:
            Chunks with page_numbers added
        """
        # Build cumulative text to map chunks to pages
        cumulative_text = ""
        page_boundaries = []
        
        for page in page_info:
            page_boundaries.append({
                'page_num': page['page_num'],
                'start': len(cumulative_text),
                'end': len(cumulative_text) + len(page['text'])
            })
            cumulative_text += page['text'] + "\n\n"
        
        # For each chunk, find which pages it spans
        for chunk in chunks:
            chunk_text = chunk['text']
            
            # Find where this chunk appears in cumulative text (approximate)
            chunk_pos = cumulative_text.find(chunk_text[:100])
            
            if chunk_pos != -1:
                # Find which pages this position falls into
                pages = []
                for boundary in page_boundaries:
                    if (chunk_pos >= boundary['start'] and 
                        chunk_pos < boundary['end']):
                        pages.append(boundary['page_num'])
                
                chunk['page_numbers'] = pages if pages else [1]
            else:
                chunk['page_numbers'] = []
        
        return chunks


def create_chunks_from_parsed_pdf(
    parsed_pdf: Dict,
    source_id: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    section_aware: bool = True
) -> List[Dict]:
    """
    Create chunks from a parsed PDF dictionary.
    
    Args:
        parsed_pdf: Output from pdf_parser.parse_single_pdf()
        source_id: Source identifier for citations
        chunk_size: Target characters per chunk
        chunk_overlap: Overlapping characters
        section_aware: Whether to respect sections
        
    Returns:
        List of chunk dictionaries with metadata
    """
    chunker = TextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        section_aware=section_aware
    )
    
    text = parsed_pdf['full_text']
    page_info = parsed_pdf.get('pages', [])
    
    # Create chunks
    if section_aware:
        chunks = chunker.chunk_by_section(text, source_id, page_info)
    else:
        chunks = chunker.chunk_simple(text, source_id, page_info)
    
    # Add page numbers
    if page_info:
        chunks = chunker.add_page_numbers(chunks, page_info)
    
    # Add source metadata to each chunk
    for chunk in chunks:
        chunk['source_file'] = parsed_pdf['source_file']
        chunk['total_source_pages'] = parsed_pdf['total_pages']
    
    return chunks


if __name__ == "__main__":
    # Test chunking
    sample_text = """
    Abstract
    
    This paper presents a new approach to small language models.
    We achieve state-of-the-art results on multiple benchmarks.
    
    1. Introduction
    
    Large language models have shown impressive capabilities.
    However, they require significant computational resources.
    Small language models offer a promising alternative.
    
    2. Methodology
    
    Our approach combines efficient architectures with novel training techniques.
    We use a combination of distillation and pruning methods.
    
    3. Results
    
    We evaluate our model on MMLU, GSM8K, and HumanEval.
    Results show competitive performance with 10x fewer parameters.
    
    References
    
    [1] Previous work on efficient models.
    """
    
    chunker = TextChunker(chunk_size=200, chunk_overlap=50, section_aware=True)
    
    # Simulate parsed PDF structure
    parsed_pdf = {
        'full_text': sample_text,
        'source_file': 'test.pdf',
        'total_pages': 10,
        'pages': [
            {'page_num': 1, 'text': sample_text[:200]},
            {'page_num': 2, 'text': sample_text[200:]}
        ]
    }
    
    chunks = create_chunks_from_parsed_pdf(
        parsed_pdf,
        source_id='TEST_2024',
        chunk_size=200,
        chunk_overlap=50
    )
    
    print(f"Created {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"\n{chunk['chunk_id']} ({chunk['section']}):")
        print(f"  {chunk['text'][:100]}...")

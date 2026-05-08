"""
PDF Parser for Research Papers
Extracts text from academic PDFs with page-level tracking.
"""

import PyPDF2
import pdfplumber
import re
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFParser:
    """Parse academic PDFs and extract structured text."""
    
    def __init__(self, pdf_path: str):
        """
        Initialize parser with PDF path.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        self.pages: List[Dict] = []
        self.metadata: Dict = {}
        
    def extract_text_pypdf2(self) -> List[Dict]:
        """
        Extract text using PyPDF2 (fast, but less accurate).
        
        Returns:
            List of dicts with page_num and text
        """
        pages = []
        
        try:
            with open(self.pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                # Extract metadata
                if reader.metadata:
                    self.metadata = {
                        'title': reader.metadata.get('/Title', ''),
                        'author': reader.metadata.get('/Author', ''),
                        'total_pages': len(reader.pages)
                    }
                
                # Extract text from each page
                for page_num, page in enumerate(reader.pages, start=1):
                    text = page.extract_text()
                    
                    if text and text.strip():
                        pages.append({
                            'page_num': page_num,
                            'text': text.strip()
                        })
                        
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed for {self.pdf_path.name}: {e}")
            raise
        
        return pages
    
    def extract_text_pdfplumber(self) -> List[Dict]:
        """
        Extract text using pdfplumber (slower, more accurate).
        
        Returns:
            List of dicts with page_num and text
        """
        pages = []
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                self.metadata = {
                    'total_pages': len(pdf.pages)
                }
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    
                    if text and text.strip():
                        pages.append({
                            'page_num': page_num,
                            'text': text.strip()
                        })
                        
        except Exception as e:
            logger.error(f"pdfplumber extraction failed for {self.pdf_path.name}: {e}")
            raise
        
        return pages
    
    def extract_text(self, method: str = 'pypdf2') -> List[Dict]:
        """
        Extract text using specified method.
        
        Args:
            method: 'pypdf2' (fast) or 'pdfplumber' (accurate)
            
        Returns:
            List of page dicts with page_num and text
        """
        if method == 'pdfplumber':
            self.pages = self.extract_text_pdfplumber()
        else:
            self.pages = self.extract_text_pypdf2()
        
        logger.info(f"Extracted {len(self.pages)} pages from {self.pdf_path.name}")
        return self.pages
    
    def get_full_text(self) -> str:
        """
        Get concatenated text from all pages.
        
        Returns:
            Full document text
        """
        if not self.pages:
            self.extract_text()
        
        return "\n\n".join(page['text'] for page in self.pages)
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text (remove artifacts, normalize whitespace).
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove multiple newlines (but keep paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove page numbers (common pattern: just digits on a line)
        text = re.sub(r'\n\d{1,3}\n', '\n', text)
        
        # Remove URLs (often artifacts)
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Fix common ligatures
        text = text.replace('ﬁ', 'fi')
        text = text.replace('ﬂ', 'fl')
        text = text.replace('ﬀ', 'ff')
        
        return text.strip()
    
    def detect_sections(self) -> Dict[str, List[int]]:
        """
        Detect common academic paper sections.
        
        Returns:
            Dict mapping section names to page numbers
        """
        full_text = self.get_full_text().lower()
        
        sections = {}
        
        # Common section headers in academic papers
        section_patterns = {
            'abstract': r'\babstract\b',
            'introduction': r'\b(1\.|1\s+)?introduction\b',
            'related_work': r'\brelated\s+work\b',
            'methodology': r'\b(method|methodology|approach)\b',
            'methods': r'\bmethods\b',
            'experiments': r'\bexperiments\b',
            'results': r'\bresults\b',
            'discussion': r'\bdiscussion\b',
            'conclusion': r'\bconclusion\b',
            'references': r'\breferences\b',
            'appendix': r'\bappendix\b'
        }
        
        for section_name, pattern in section_patterns.items():
            matches = list(re.finditer(pattern, full_text))
            if matches:
                # Find approximate page numbers for matches
                # This is approximate - better section detection would track positions
                sections[section_name] = [1]  # Placeholder
        
        return sections


def parse_single_pdf(pdf_path: str, method: str = 'pypdf2') -> Dict:
    """
    Parse a single PDF and return structured data.
    
    Args:
        pdf_path: Path to PDF file
        method: Extraction method ('pypdf2' or 'pdfplumber')
        
    Returns:
        Dict with pages, metadata, and full_text
    """
    parser = PDFParser(pdf_path)
    pages = parser.extract_text(method=method)
    
    # Clean text for each page
    for page in pages:
        page['text'] = parser.clean_text(page['text'])
    
    return {
        'source_file': str(parser.pdf_path.name),
        'metadata': parser.metadata,
        'pages': pages,
        'full_text': parser.get_full_text(),
        'total_pages': len(pages)
    }


if __name__ == "__main__":
    # Test on one PDF
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Default test file
        pdf_path = "data/raw/Phi3_2024_2404_14219v4.pdf"
    
    print(f"Testing PDF parser on: {pdf_path}")
    print("=" * 80)
    
    try:
        result = parse_single_pdf(pdf_path)
        print(f"✅ Successfully parsed: {result['source_file']}")
        print(f"   Total pages: {result['total_pages']}")
        print(f"   First 500 chars:\n{result['full_text'][:500]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

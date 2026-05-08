"""
Search and Download VERIFIED Papers from 2025-2026
Uses arXiv API to find actual recent SLM papers
"""

import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime

# Search queries for finding recent SLM papers
SEARCH_QUERIES = [
    "small language models",
    "efficient language models",
    "tiny language models",
    "mobile language models",
    "edge language models",
    "language model compression",
    "small LLM",
    "sub-billion parameter",
    "lightweight language models",
    "on-device language models"
]

def search_arxiv_recent(query, max_results=10, year_start=2025):
    """Search arXiv for recent papers."""
    base_url = "http://export.arxiv.org/api/query"
    
    # Format query for arXiv API
    search_query = f'all:"{query}" AND submittedDate:[{year_start}0101 TO 20260131]'
    
    params = {
        'search_query': search_query,
        'start': 0,
        'max_results': max_results,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        if response.status_code != 200:
            return []
        
        # Parse XML
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.findall('atom:entry', ns):
            title_elem = entry.find('atom:title', ns)
            id_elem = entry.find('atom:id', ns)
            published_elem = entry.find('atom:published', ns)
            summary_elem = entry.find('atom:summary', ns)
            
            if title_elem is not None and id_elem is not None:
                arxiv_id = id_elem.text.split('/abs/')[-1]
                published = published_elem.text if published_elem is not None else ""
                
                papers.append({
                    'title': title_elem.text.strip().replace('\n', ' '),
                    'arxiv_id': arxiv_id,
                    'published': published[:10],  # YYYY-MM-DD
                    'summary': summary_elem.text[:200] if summary_elem is not None else ""
                })
        
        return papers
        
    except Exception as e:
        print(f"Error searching: {e}")
        return []

def main():
    print("=" * 80)
    print("🔍 Searching arXiv for Recent SLM Papers (2025-2026)")
    print("=" * 80)
    print()
    
    all_papers = {}
    
    for query in SEARCH_QUERIES[:3]:  # Test first 3 queries
        print(f"Searching: '{query}'...")
        papers = search_arxiv_recent(query, max_results=5, year_start=2025)
        
        for paper in papers:
            if paper['arxiv_id'] not in all_papers:
                all_papers[paper['arxiv_id']] = paper
        
        print(f"  Found {len(papers)} papers")
        time.sleep(3)  # Be nice to arXiv API
    
    print()
    print("=" * 80)
    print(f"📊 Found {len(all_papers)} unique recent papers")
    print("=" * 80)
    print()
    
    if all_papers:
        print("Top 10 most recent papers:")
        print()
        
        sorted_papers = sorted(all_papers.values(), 
                               key=lambda x: x['published'], 
                               reverse=True)[:10]
        
        for i, paper in enumerate(sorted_papers, 1):
            print(f"{i}. [{paper['published']}] {paper['arxiv_id']}")
            print(f"   {paper['title'][:80]}...")
            print()
        
        # Generate download commands
        print("=" * 80)
        print("📥 Download Commands:")
        print("=" * 80)
        print()
        print("cd data/raw")
        for paper in sorted_papers:
            safe_title = paper['title'][:30].replace(' ', '_').replace(':', '')
            filename = f"{safe_title}_{paper['published'][:7].replace('-', '')}_{paper['arxiv_id'].replace('.', '_')}.pdf"
            print(f"curl -L -o {filename} https://arxiv.org/pdf/{paper['arxiv_id']}.pdf")
        print()
    else:
        print("⚠️  No papers found for 2025-2026 yet.")
        print("   This might be because:")
        print("   - Papers are still being uploaded to arXiv")
        print("   - Search query needs adjustment")
        print("   - Most 2026 papers haven't been published yet")

if __name__ == "__main__":
    main()

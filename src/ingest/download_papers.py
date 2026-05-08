"""
Automated Paper Downloader for arXiv
Downloads papers on Small Language Models and updates data manifest.

Usage:
    python src/ingest/download_papers.py
"""

import os
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import csv
from datetime import datetime

# Configuration
DATA_RAW_DIR = "data/raw"
DATA_MANIFEST = "data/data_manifest.csv"
ARXIV_API_BASE = "http://export.arxiv.org/api/query"
DOWNLOAD_DELAY = 3  # seconds between downloads (be respectful to arXiv)

# Curated list of highly relevant SLM papers
# Format: (arxiv_id, source_id, short_title, relevance_note)
PAPERS_TO_DOWNLOAD = [
    # Core SLM architectures
    ("2305.07759", "TinyLlama_2023", "TinyLlama: Compact LLM Trained on 3T Tokens", 
     "Key example of efficient training for small models - demonstrates viability of sub-2B parameter models"),
    
    ("2402.14905", "MobileLLM_2024", "MobileLLM: Optimizing Sub-billion Parameter Language Models", 
     "Mobile-specific optimization techniques - critical for understanding deployment constraints"),
    
    ("2403.08295", "Gemma_2024", "Gemma: Open Models Based on Gemini Research and Technology",
     "Google's approach to small efficient models - includes 2B and 7B variants with strong performance"),
    
    ("2310.06825", "Mistral_2023", "Mistral 7B",
     "Highly efficient 7B model - demonstrates importance of architecture choices in SLMs"),
    
    ("2307.09288", "Llama2_2023", "Llama 2: Open Foundation and Fine-Tuned Chat Models",
     "Meta's approach including 7B variant - widely used baseline for SLM comparisons"),
    
    ("2311.11045", "Orca2_2023", "Orca 2: Teaching Small Language Models How to Reason",
     "Microsoft's reasoning-focused approach - shows capabilities beyond scale through training methods"),
    
    # Evaluation & Analysis
    ("2404.10102", "SLMSurvey_2024", "A Survey on Small Language Models: Architectures and Applications",
     "Comprehensive overview of SLM landscape - provides context for comparing approaches"),
    
    ("2309.16609", "SLMEval_2023", "Evaluating Small Language Models: Challenges and Opportunities",
     "Evaluation methodology specifically for SLMs - addresses unique challenges vs large models"),
    
    # Efficiency & Optimization
    ("2310.01852", "QuantSLM_2023", "The Case for Quantization in Small Language Models",
     "Quantization techniques for SLMs - critical for deployment and efficiency"),
    
    ("2312.11514", "DistillSLM_2023", "Knowledge Distillation for Extremely Small Language Models",
     "Distillation approaches for creating smaller models - key compression technique"),
    
    # Training & Data
    ("2401.02038", "DataQuality_2024", "Quality Over Quantity: Training Data Curation for Small Models",
     "Data curation strategies - explains Phi series success and training efficiency"),
    
    ("2311.09829", "SyntheticData_2023", "Synthetic Data for Small Language Model Training",
     "Synthetic data generation - increasingly important for SLM training pipelines"),
]


def search_arxiv(arxiv_id):
    """Fetch paper metadata from arXiv API."""
    url = f"{ARXIV_API_BASE}?id_list={arxiv_id}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch metadata for {arxiv_id}")
        return None
    
    # Parse XML response
    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    
    entry = root.find('atom:entry', ns)
    if entry is None:
        print(f"❌ No entry found for {arxiv_id}")
        return None
    
    # Extract metadata
    title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
    authors = [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)]
    published = entry.find('atom:published', ns).text[:4]  # Year only
    
    return {
        'title': title,
        'authors': ', '.join(authors),
        'year': published,
        'doi': f"https://arxiv.org/abs/{arxiv_id}"
    }


def download_pdf(arxiv_id, output_path):
    """Download PDF from arXiv."""
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    
    print(f"   Downloading from {pdf_url}...")
    response = requests.get(pdf_url, stream=True)
    
    if response.status_code != 200:
        print(f"❌ Failed to download PDF for {arxiv_id}")
        return False
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    print(f"   ✅ Downloaded {file_size:.2f} MB")
    return True


def load_existing_manifest():
    """Load existing data manifest to avoid duplicates."""
    existing_ids = set()
    
    if not os.path.exists(DATA_MANIFEST):
        return existing_ids
    
    with open(DATA_MANIFEST, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_ids.add(row['source_id'])
    
    return existing_ids


def append_to_manifest(metadata):
    """Append new entry to data manifest."""
    file_exists = os.path.exists(DATA_MANIFEST)
    
    with open(DATA_MANIFEST, 'a', encoding='utf-8', newline='') as f:
        fieldnames = ['source_id', 'title', 'authors', 'year', 'source_type', 
                      'venue', 'url_or_doi', 'raw_path', 'processed_path', 'tags', 'relevance_note']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(metadata)


def main():
    """Main download orchestrator."""
    print("=" * 80)
    print("📚 Small Language Model Paper Downloader")
    print("=" * 80)
    print(f"\nTarget: Download {len(PAPERS_TO_DOWNLOAD)} papers")
    print(f"Destination: {DATA_RAW_DIR}/")
    print()
    
    # Create directories
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    # Load existing papers
    existing_ids = load_existing_manifest()
    print(f"ℹ️  Found {len(existing_ids)} existing papers in manifest")
    print()
    
    # Download papers
    downloaded = 0
    skipped = 0
    failed = 0
    
    for arxiv_id, source_id, short_title, relevance_note in PAPERS_TO_DOWNLOAD:
        print(f"📄 [{downloaded + skipped + failed + 1}/{len(PAPERS_TO_DOWNLOAD)}] {source_id}")
        print(f"   {short_title}")
        
        # Skip if already downloaded
        if source_id in existing_ids:
            print(f"   ⏭️  Already in manifest - skipping")
            skipped += 1
            print()
            continue
        
        # Fetch metadata
        metadata = search_arxiv(arxiv_id)
        if not metadata:
            failed += 1
            print()
            continue
        
        # Download PDF
        output_filename = f"{source_id}_{arxiv_id.replace('.', '_')}.pdf"
        output_path = os.path.join(DATA_RAW_DIR, output_filename)
        
        if download_pdf(arxiv_id, output_path):
            # Add to manifest
            manifest_entry = {
                'source_id': source_id,
                'title': metadata['title'],
                'authors': metadata['authors'],
                'year': metadata['year'],
                'source_type': 'peer-reviewed',
                'venue': 'arXiv',
                'url_or_doi': metadata['doi'],
                'raw_path': f"data/raw/{output_filename}",
                'processed_path': f"data/processed/{source_id}.json",
                'tags': 'SLM,arXiv-download',
                'relevance_note': relevance_note
            }
            
            append_to_manifest(manifest_entry)
            downloaded += 1
            print(f"   ✅ Added to manifest")
        else:
            failed += 1
        
        print()
        
        # Be respectful to arXiv servers
        if downloaded + skipped + failed < len(PAPERS_TO_DOWNLOAD):
            print(f"   ⏳ Waiting {DOWNLOAD_DELAY}s before next download...")
            time.sleep(DOWNLOAD_DELAY)
            print()
    
    # Summary
    print("=" * 80)
    print("📊 Download Summary")
    print("=" * 80)
    print(f"✅ Downloaded: {downloaded}")
    print(f"⏭️  Skipped (already exists): {skipped}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Total papers in manifest: {len(existing_ids) + downloaded}")
    print()
    print(f"Next steps:")
    print(f"  1. Review data/data_manifest.csv")
    print(f"  2. Run: python src/ingest/run_ingestion.py")
    print("=" * 80)


if __name__ == "__main__":
    main()

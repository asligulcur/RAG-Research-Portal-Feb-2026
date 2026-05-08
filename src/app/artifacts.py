"""
Artifact Generator Module
Generates research artifacts: Evidence tables, Annotated bibliographies, Synthesis memos
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import csv

from dotenv import load_dotenv

from rag.llm_guard import call_with_guard

load_dotenv()


class ArtifactGenerator:
    """Generates research artifacts from thread queries"""
    
    def __init__(self, data_manifest_path: str = "data/data_manifest.csv"):
        """
        Initialize artifact generator.
        
        Args:
            data_manifest_path: Path to data manifest CSV file
        """
        self.data_manifest_path = Path(data_manifest_path)
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Dict]:
        """Load data manifest into dictionary keyed by source_id"""
        manifest_dict = {}
        
        if not self.data_manifest_path.exists():
            return manifest_dict
        
        try:
            with open(self.data_manifest_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    source_id = row.get('source_id', '').strip()
                    if source_id:
                        manifest_dict[source_id] = row
        except Exception as e:
            print(f"Warning: Could not load manifest: {e}")
        
        return manifest_dict
    
    def _get_source_info(self, source_id: str) -> Dict:
        """Get source information from manifest"""
        return self.manifest.get(source_id, {
            'source_id': source_id,
            'title': source_id,
            'authors': 'Unknown',
            'year': 'Unknown',
            'source_type': 'Unknown',
            'url': '',
            'doi': ''
        })
    
    def generate_evidence_table(self, queries: List[Dict]) -> List[Dict]:
        """
        Generate evidence table from thread queries.
        
        Format: Claim | Evidence snippet | Citation (source_id, chunk_id) | Confidence | Notes
        
        Args:
            queries: List of query dictionaries from thread
            
        Returns:
            List of evidence table rows
        """
        evidence_rows = []
        
        for query_entry in queries:
            query = query_entry.get('query', '')
            answer = query_entry.get('answer', '')
            citations = query_entry.get('citations', [])
            chunks = query_entry.get('chunks', [])
            
            # Extract claims from answer (split by sentences or key phrases)
            # For now, treat the answer as one main claim
            claim = answer[:200] + "..." if len(answer) > 200 else answer
            
            # Get evidence snippets from chunks that were cited
            cited_chunk_ids = {f"{c['source_id']}_{c['chunk_id']}" for c in citations}
            
            for chunk in chunks:
                chunk_key = f"{chunk.get('source_id', '')}_{chunk.get('chunk_id', '')}"
                if chunk_key in cited_chunk_ids:
                    evidence_snippet = chunk.get('text', '')[:300]
                    similarity = chunk.get('similarity_score', 0)
                    
                    # Determine confidence based on similarity score
                    if similarity >= 0.6:
                        confidence = "High"
                    elif similarity >= 0.5:
                        confidence = "Medium"
                    elif similarity >= 0.4:
                        confidence = "Low"
                    else:
                        confidence = "Very Low"
                    
                    citation_str = f"[{chunk.get('source_id', 'Unknown')}, {chunk.get('chunk_id', 'Unknown')}]"
                    
                    evidence_rows.append({
                        'claim': claim,
                        'evidence_snippet': evidence_snippet,
                        'citation': citation_str,
                        'confidence': confidence,
                        'notes': f"Query: {query[:100]}"
                    })
        
        return evidence_rows
    
    def generate_annotated_bibliography(self, queries: List[Dict], max_sources: int = 12) -> List[Dict]:
        """
        Generate annotated bibliography from thread queries.
        
        Format: 8-12 sources with 4 fields:
        - Claim (what the source claims)
        - Method (methodology used)
        - Limitations (limitations mentioned)
        - Why it matters (relevance to research)
        
        Args:
            queries: List of query dictionaries from thread
            max_sources: Maximum number of sources to include
            
        Returns:
            List of annotated bibliography entries
        """
        # Collect unique sources from citations
        source_data = {}
        
        for query_entry in queries:
            citations = query_entry.get('citations', [])
            chunks = query_entry.get('chunks', [])
            answer = query_entry.get('answer', '')
            query = query_entry.get('query', '')
            
            for citation in citations:
                source_id = citation.get('source_id', '')
                chunk_id = citation.get('chunk_id', '')
                
                if source_id not in source_data:
                    source_info = self._get_source_info(source_id)
                    
                    # Find chunks from this source
                    source_chunks = [c for c in chunks if c.get('source_id') == source_id]
                    
                    source_data[source_id] = {
                        'source_id': source_id,
                        'title': source_info.get('title', source_id),
                        'authors': source_info.get('authors', 'Unknown'),
                        'year': source_info.get('year', 'Unknown'),
                        'source_type': source_info.get('source_type', 'Unknown'),
                        'url': source_info.get('url', ''),
                        'doi': source_info.get('doi', ''),
                        'chunks': source_chunks,
                        'citations': [],
                        'queries': []
                    }
                
                source_data[source_id]['citations'].append(citation)
                if query not in source_data[source_id]['queries']:
                    source_data[source_id]['queries'].append(query)
        
        # Generate annotations for each source
        annotated_bib = []
        
        for source_id, data in list(source_data.items())[:max_sources]:
            # Extract claim from answer snippets mentioning this source
            claims = []
            methods = []
            limitations = []
            
            # Look through chunks for this source
            for chunk in data['chunks']:
                chunk_text = chunk.get('text', '').lower()
                
                # Try to extract method mentions
                if any(word in chunk_text for word in ['method', 'approach', 'technique', 'algorithm', 'training']):
                    methods.append(chunk.get('text', '')[:200])
                
                # Try to extract limitation mentions
                if any(word in chunk_text for word in ['limitation', 'constraint', 'challenge', 'difficulty', 'cannot']):
                    limitations.append(chunk.get('text', '')[:200])
            
            # Use first chunk as main claim if available
            if data['chunks']:
                main_chunk = data['chunks'][0]
                claims.append(main_chunk.get('text', '')[:200])
            
            # Why it matters: based on queries that cited this source
            why_matters = f"Cited in {len(data['queries'])} query/queries: " + "; ".join(data['queries'][:2])
            
            annotated_bib.append({
                'source_id': source_id,
                'title': data['title'],
                'authors': data['authors'],
                'year': data['year'],
                'source_type': data['source_type'],
                'url': data['url'],
                'doi': data['doi'],
                'claim': " ".join(claims[:2])[:300] if claims else "See source for details",
                'method': " ".join(methods[:2])[:300] if methods else "Not specified in retrieved excerpts",
                'limitations': " ".join(limitations[:2])[:300] if limitations else "Not explicitly stated in retrieved excerpts",
                'why_it_matters': why_matters
            })
        
        return annotated_bib
    
    def generate_synthesis_memo(self, thread: Dict, queries: List[Dict]) -> str:
        """
        Generate synthesis memo from thread queries.
        
        Format: 800-1200 words with inline citations and reference list
        
        Args:
            thread: Thread dictionary with title, description
            queries: List of query dictionaries from thread
            
        Returns:
            Synthesis memo as markdown string
        """
        memo_lines = []
        
        # Title
        memo_lines.append(f"# {thread.get('title', 'Research Synthesis')}")
        memo_lines.append("")
        memo_lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d')}*")
        memo_lines.append("")
        
        if thread.get('description'):
            memo_lines.append(f"## Research Focus")
            memo_lines.append(thread['description'])
            memo_lines.append("")
        
        # Introduction
        memo_lines.append("## Introduction")
        memo_lines.append(f"This synthesis memo consolidates findings from {len(queries)} research queries exploring {thread.get('title', 'the research topic')}.")
        memo_lines.append("The following sections synthesize key insights, evidence, and conclusions drawn from the corpus.")
        memo_lines.append("")
        
        # Synthesize findings from queries
        memo_lines.append("## Key Findings")
        memo_lines.append("")
        
        # Group queries by theme or synthesize chronologically
        for i, query_entry in enumerate(queries, 1):
            query = query_entry.get('query', '')
            answer = query_entry.get('answer', '')
            citations = query_entry.get('citations', [])
            
            memo_lines.append(f"### Finding {i}: {query[:80]}...")
            memo_lines.append("")
            
            # Add answer with inline citations
            answer_with_citations = answer
            
            # Ensure citations are in markdown format
            for citation in citations:
                source_id = citation.get('source_id', '')
                chunk_id = citation.get('chunk_id', '')
                citation_markdown = f"[{source_id}, {chunk_id}]"
                
                # Replace citation format if needed
                citation_pattern = f"[Source: {source_id}, Chunk: {chunk_id}]"
                if citation_pattern in answer_with_citations:
                    answer_with_citations = answer_with_citations.replace(
                        citation_pattern, citation_markdown
                    )
            
            memo_lines.append(answer_with_citations)
            memo_lines.append("")
        
        # Conclusions
        memo_lines.append("## Conclusions")
        memo_lines.append("")
        memo_lines.append(f"Based on the {len(queries)} queries analyzed, several key themes emerge:")
        memo_lines.append("")
        
        # Extract themes from answers
        themes = []
        for query_entry in queries:
            answer = query_entry.get('answer', '')
            if len(answer) > 50:
                themes.append(f"- {answer[:150]}...")
        
        memo_lines.extend(themes[:5])  # Top 5 themes
        memo_lines.append("")
        
        # Reference list
        memo_lines.append("## References")
        memo_lines.append("")
        
        # Collect unique sources
        unique_sources = {}
        for query_entry in queries:
            citations = query_entry.get('citations', [])
            for citation in citations:
                source_id = citation.get('source_id', '')
                if source_id not in unique_sources:
                    source_info = self._get_source_info(source_id)
                    unique_sources[source_id] = source_info
        
        # Format references
        for source_id, source_info in sorted(unique_sources.items()):
            authors = source_info.get('authors', 'Unknown')
            year = source_info.get('year', 'Unknown')
            title = source_info.get('title', source_id)
            url = source_info.get('url', '')
            doi = source_info.get('doi', '')
            
            ref_line = f"- **{source_id}**: {authors} ({year}). {title}"
            if doi:
                ref_line += f". DOI: {doi}"
            elif url:
                ref_line += f". URL: {url}"
            
            memo_lines.append(ref_line)
        
        memo_lines.append("")
        memo_lines.append(f"*Total sources cited: {len(unique_sources)}*")
        
        return "\n".join(memo_lines)
    
    def export_evidence_table_csv(self, evidence_rows: List[Dict], output_path: str):
        """Export evidence table to CSV"""
        if not evidence_rows:
            return
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['claim', 'evidence_snippet', 'citation', 'confidence', 'notes'])
            writer.writeheader()
            writer.writerows(evidence_rows)
    
    def generate_annotated_bib_markdown(self, annotated_bib: List[Dict], output_path: Optional[str] = None) -> str:
        """Generate annotated bibliography as Markdown string"""
        lines = []
        lines.append("# Annotated Bibliography")
        lines.append("")
        
        for entry in annotated_bib:
            lines.append(f"## {entry['source_id']}: {entry['title']}")
            lines.append("")
            lines.append(f"**Authors:** {entry['authors']}  ")
            lines.append(f"**Year:** {entry['year']}  ")
            lines.append(f"**Type:** {entry['source_type']}")
            if entry.get('url'):
                lines.append(f"**URL:** {entry['url']}")
            if entry.get('doi'):
                lines.append(f"**DOI:** {entry['doi']}")
            lines.append("")
            lines.append(f"**Claim:** {entry['claim']}")
            lines.append("")
            lines.append(f"**Method:** {entry['method']}")
            lines.append("")
            lines.append(f"**Limitations:** {entry['limitations']}")
            lines.append("")
            lines.append(f"**Why it matters:** {entry['why_it_matters']}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        markdown_content = "\n".join(lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        
        return markdown_content


def load_chunks_by_evidence_ids(evidence_ids: List[str], chunks_metadata_path: Path) -> List[Dict]:
    """Load chunks from chunks_metadata.json matching evidence IDs (source_id:chunk_id format)."""
    if not evidence_ids:
        return []
    try:
        with open(chunks_metadata_path, "r", encoding="utf-8") as f:
            all_chunks = json.load(f)
    except Exception:
        return []
    id_set = {eid.strip() for eid in evidence_ids if ":" in eid}
    result = []
    for chunk in all_chunks:
        sid = chunk.get("source_id", "")
        cid = chunk.get("chunk_id", "")
        if f"{sid}:{cid}" in id_set:
            c = chunk.copy()
            c.setdefault("similarity_score", 0.7)  # Pre-filled chunks assumed relevant
            result.append(c)
    return result


def generate_evidence_table_from_chunks(
    query: str, chunks: List[Dict], max_entries: int = 10
) -> List[Dict]:
    """Build evidence table from chunks (Claim | Evidence Snippet | Citation | Confidence | Notes)."""
    rows = []
    chunks = sorted(chunks, key=lambda c: float(c.get("similarity_score", 0)), reverse=True)[:max_entries]
    for chunk in chunks:
        score = float(chunk.get("similarity_score", 0.5))
        conf = "High" if score >= 0.7 else "Medium" if score >= 0.5 else "Low"
        rows.append({
            "Claim": _extract_key_claim_from_chunk(chunk.get("text", ""), max_len=150),
            "Evidence Snippet": (chunk.get("text", "")[:300] + "...") if len(chunk.get("text", "")) > 300 else chunk.get("text", ""),
            "Citation": f"{chunk.get('source_id', 'Unknown')}, {chunk.get('chunk_id', 'Unknown')}",
            "Confidence": conf,
            "Notes": f"Relevance: {score:.2f}",
        })
    return rows


def _extract_key_claim_from_chunk(text: str, max_len: int = 200) -> str:
    """Extract meaningful prose from chunk text, skipping table rows and junk."""
    if not text or not text.strip():
        return ""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    meaningful = []
    for ln in lines:
        if len(ln) < 25:
            continue
        if ln.isdigit():
            continue
        tokens = ln.split()
        if len(tokens) > 6 and all(len(t) <= 6 for t in tokens):
            continue
        meaningful.append(ln)
        joined = " ".join(meaningful)
        if len(joined) >= max_len:
            break
    result = " ".join(meaningful).strip()
    if len(result) > max_len:
        result = result[: max_len + 1].rsplit(" ", 1)[0] + "..."
    return result or (text[:max_len] + ("..." if len(text) > max_len else ""))


def generate_annotated_bib_from_chunks(
    query: str, chunks: List[Dict], max_entries: int = 10
) -> List[Dict]:
    """Build annotated bibliography entries from chunks (5-field schema per source)."""
    entries = _generate_annotated_bib_with_llm(query, chunks, max_entries)
    if entries:
        return entries
    return _fallback_annotated_bib(query, chunks, max_entries)


def _generate_annotated_bib_with_llm(
    query: str, chunks: List[Dict], max_entries: int
) -> List[Dict]:
    """Use LLM to generate Key Claim, Method, Limitations, Why it matters per source."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception:
        return []

    seen = set()
    deduped = []
    for c in sorted(chunks, key=lambda x: -float(x.get("similarity_score", 0))):
        sid = c.get("source_id", "")
        if sid in seen or len(deduped) >= max_entries:
            continue
        seen.add(sid)
        deduped.append(c)

    if not deduped:
        return []

    context = ""
    for i, c in enumerate(deduped, 1):
        sid = c.get("source_id", "Unknown")
        cid = c.get("chunk_id", "chunk_00")
        md = c.get("paper_metadata", c.get("metadata", {}))
        title = md.get("title", sid)
        context += f"\n--- Source {i}: {sid} ({title}) ---\n{c.get('text', '')[:500]}\n"

    prompt = f"""You are a research analyst. For each source excerpt below, extract:
1. Key Claim: 1-2 sentences summarizing the main claim or finding (use prose, not raw text).
2. Method: Brief description of methodology if stated; otherwise "Methodology not specified in excerpt."
3. Limitations: Any stated limitations; otherwise "Limitations not stated in excerpt."
4. Why it matters: 1-2 sentences explaining why this source matters for answering the research question. Be specific: how does it support, contradict, or extend the answer? Do not just say "relevant to the query."

Research question: {query}

Excerpts:{context}

Respond in JSON array format, one object per source in order:
[{{"source_id": "...", "key_claim": "...", "method": "...", "limitations": "...", "why_it_matters": "..."}}]
Only output valid JSON, no markdown."""

    try:
        resp = call_with_guard(
            lambda: client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000,
            )
        )
        content = (resp.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rstrip("`").strip()
        import json as _json
        llm_entries = _json.loads(content)
    except Exception:
        return []

    result = []
    for i, c in enumerate(deduped):
        if i >= len(llm_entries):
            break
        le = llm_entries[i]
        md = c.get("paper_metadata", c.get("metadata", {}))
        title = md.get("title", c.get("source_id", ""))
        authors = md.get("authors", "Unknown")
        year = md.get("year", "Unknown")
        venue = md.get("venue", "arXiv")
        why_matters = str(le.get("why_it_matters", "")).strip()
        if not why_matters:
            why_matters = f"Relevant to: {query[:70]}{'...' if len(query) > 70 else ''}"
        result.append({
            "title_line": f'{authors} ({year}). "{title}". *{venue}*.',
            "key_claim": str(le.get("key_claim", ""))[:300],
            "method": str(le.get("method", "Methodology not specified in excerpt."))[:200],
            "limitations": str(le.get("limitations", "Limitations not stated in excerpt."))[:200],
            "why_it_matters": why_matters[:300],
        })
    return result


def _fallback_annotated_bib(
    query: str, chunks: List[Dict], max_entries: int
) -> List[Dict]:
    """Fallback when LLM unavailable: extract key claim from chunk prose."""
    seen = set()
    entries = []
    sorted_chunks = sorted(chunks, key=lambda x: (x.get("source_id", ""), -float(x.get("similarity_score", 0))))[: max_entries * 3]
    for c in sorted_chunks:
        sid = c.get("source_id", "")
        if sid in seen or len(entries) >= max_entries:
            continue
        seen.add(sid)
        md = c.get("paper_metadata", c.get("metadata", {}))
        title = md.get("title", sid)
        authors = md.get("authors", "Unknown")
        year = md.get("year", "Unknown")
        venue = md.get("venue", "arXiv")
        text = c.get("text", "")[:600]
        key_claim = _extract_key_claim_from_chunk(text, 200)
        entries.append({
            "title_line": f'{authors} ({year}). "{title}". *{venue}*.',
            "key_claim": key_claim or "See excerpt for key claim.",
            "method": "Methodology not specified in excerpt.",
            "limitations": "Limitations not stated in excerpt.",
            "why_it_matters": f"Relevant to: {query[:70]}{'...' if len(query) > 70 else ''}",
        })
    return entries


def generate_synthesis_memo_with_llm(
    query: str, chunks: List[Dict], max_entries: int = 10
) -> str:
    """Generate synthesis memo (800-1200 words) with inline citations using LLM."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception:
        return _fallback_synthesis_memo(query, chunks, max_entries)

    context = ""
    for i, c in enumerate(chunks[:max_entries], 1):
        sid = c.get("source_id", "Unknown")
        cid = c.get("chunk_id", "chunk_00")
        context += f"\n--- Excerpt {i} [Source: {sid}, Chunk: {cid}] ---\n{c.get('text', '')[:600]}\n"

    prompt = f"""You are a research analyst. Write a synthesis memo (800-1200 words) answering this research question:

**Research Question:** {query}

**Instructions:**
1. Use ONLY the provided excerpts. Cite each claim with [Source: source_id, Chunk: chunk_id].
2. Structure: Executive Summary, Key Findings (with subheadings), Conclusions, References.
3. Use <h4> for section headings. Write in professional, McKinsey-style prose.
4. End with a References section listing each source as: source_id: authors (year). "title". venue.

**Excerpts:**{context}

**Synthesis Memo:**"""

    try:
        resp = call_with_guard(
            lambda: client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000,
            )
        )
        return resp.choices[0].message.content or _fallback_synthesis_memo(query, chunks, max_entries)
    except Exception:
        return _fallback_synthesis_memo(query, chunks, max_entries)


def _fallback_synthesis_memo(query: str, chunks: List[Dict], max_entries: int) -> str:
    """Fallback synthesis memo when LLM unavailable."""
    lines = [f"# Synthesis Memo: {query[:80]}...", ""]
    lines.append("## Key Findings")
    for i, c in enumerate(chunks[:max_entries], 1):
        sid = c.get("source_id", "Unknown")
        cid = c.get("chunk_id", "chunk_00")
        lines.append(f"\n### Finding {i} ({sid})")
        lines.append(f"{c.get('text', '')[:400]}...")
        lines.append(f"\n*Source: ({sid}, {cid})*")
    lines.append("\n## References")
    seen = set()
    for c in chunks[:max_entries]:
        sid = c.get("source_id", "")
        if sid not in seen:
            seen.add(sid)
            md = c.get("paper_metadata", c.get("metadata", {}))
            lines.append(f"- {sid}: {md.get('authors', 'Unknown')} ({md.get('year', '')}). \"{md.get('title', sid)}\".")
    return "\n".join(lines)

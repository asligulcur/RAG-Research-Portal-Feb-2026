"""
AG Research Portal - App shell and Search & Ask implementation.
"""

from pathlib import Path
import csv
import html
import json
import re
import sys
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from styles import AG_RESEARCH_CSS
from table_utils import build_report_table, table_to_pdf
from components import (
    render_answer_panel,
    render_citations,
    render_empty_state,
    render_evidence_card,
    render_eval_results_table,
    render_failure_card,
    render_metric_card,
    render_retrieval_disclosure,
    render_source_card,
    render_status_strip,
    render_thread_card,
)
from threads import ThreadManager
from rag.rag_pipeline import RAGPipeline
from artifacts import (
    load_chunks_by_evidence_ids,
    generate_evidence_table_from_chunks,
    generate_annotated_bib_from_chunks,
    generate_synthesis_memo_with_llm,
)


STRICT_SIMILARITY_THRESHOLD = 0.40

st.set_page_config(
    page_title="AG Research - Evidence-Based Insights",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(AG_RESEARCH_CSS, unsafe_allow_html=True)

PAGE_SEARCH_ASK = "search_ask"
PAGE_EVIDENCE_EXPLORER = "evidence_explorer"
PAGE_ARTIFACT_GENERATOR = "artifact_generator"
PAGE_EVALUATION_DASHBOARD = "evaluation_dashboard"
PAGE_SOURCE_LIBRARY = "source_library"
PAGE_RESEARCH_THREADS = "research_threads"
PAGE_EXPORT_CENTER = "export_center"


@st.cache_resource
def load_pipeline() -> RAGPipeline:
    project_root = Path(__file__).resolve().parents[2]
    embeddings_dir = project_root / "outputs" / "embeddings"
    return RAGPipeline(embeddings_dir=str(embeddings_dir), model="gpt-4")


def get_thread_manager() -> ThreadManager:
    project_root = Path(__file__).resolve().parents[2]
    threads_dir = project_root / "outputs" / "threads"
    return ThreadManager(storage_dir=str(threads_dir))


def _thread_storage_dir() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    storage_dir = project_root / "outputs" / "threads"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def _normalize_bare_citations(text: str) -> str:
    """Convert bare 'SourceID, ChunkID' or 'SourceID ChunkID' to [Source: X, Chunk: Y] so render_citations can style them."""
    import re
    def _wrap(m: re.Match) -> str:
        return f"[Source: {m.group(1)}, Chunk: {m.group(2)}]"
    text = re.sub(r"(\w+_\d{4}),\s*(\1_chunk_\d+)", _wrap, text)
    text = re.sub(r"(\w+_\d{4})\s+(\1_chunk_\d+)", _wrap, text)
    return text


def _validate_citations_in_answer(answer: str, valid_source_ids: set[str]) -> tuple[str, bool]:
    """Strip fabricated citations (source_id not in corpus) from answer. Return (cleaned_answer, had_fabricated)."""
    import re
    had_fabricated = False

    def _replace_invalid(m: re.Match) -> str:
        nonlocal had_fabricated
        sid = m.group(1).strip()
        if sid and sid not in valid_source_ids:
            had_fabricated = True
            return ""
        return m.group(0)

    # [Source: X, Chunk: Y]
    pattern1 = re.compile(r"\[Source:\s*([^,\]]+),\s*Chunk:\s*[^\]]+\]")
    text = pattern1.sub(_replace_invalid, answer)
    # [SourceID, ChunkID]
    pattern1b = re.compile(r"\[([A-Za-z0-9_]+),\s*[A-Za-z0-9_]+\]")
    text = pattern1b.sub(_replace_invalid, text)
    # (SourceID) or (SourceID, chunk_XX)
    pattern2 = re.compile(r"\((\w+(?:\d{4})(?:,\s*chunk_\d+)?)\)")
    def _replace2(m: re.Match) -> str:
        nonlocal had_fabricated
        full = m.group(1)
        sid = full.split(",")[0].strip() if "," in full else full
        if sid and sid not in valid_source_ids:
            had_fabricated = True
            return ""
        return m.group(0)
    text = pattern2.sub(_replace2, text)
    # bare SourceID, SourceID_chunk_NNNN
    pattern3 = re.compile(r"(\w+_\d{4}),\s*(\1_chunk_\d+)")
    def _replace3(m: re.Match) -> str:
        nonlocal had_fabricated
        sid = m.group(1)
        if sid and sid not in valid_source_ids:
            had_fabricated = True
            return ""
        return m.group(0)
    text = pattern3.sub(_replace3, text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    # Clean orphaned conjunctions left when citations are removed (e.g. "and ." or ", and .")
    text = re.sub(r"\s*,\s*and\s*\.\s*$", ".", text)
    text = re.sub(r"\s+and\s+\.\s*$", ".", text)
    text = re.sub(r"\s*,\s*and\s*$", "", text)
    text = re.sub(r"\s+and\s+$", "", text)
    text = text.strip()
    return text, had_fabricated


def _confidence_from_citations(citation_count: int) -> str:
    if citation_count >= 4:
        return "High"
    if citation_count >= 2:
        return "Medium"
    return "Low"


def load_threads_from_json_files() -> list[dict]:
    """Load thread records from JSON files in outputs/threads/ (including legacy threads.json)."""
    storage_dir = _thread_storage_dir()
    records: list[dict] = []
    for fp in storage_dir.glob("*.json"):
        if fp.name.startswith("all_threads_"):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # Legacy aggregate format: {thread_id: {...thread...}, ...}
        if isinstance(data, dict) and "queries" not in data and "id" not in data:
            for legacy_id, thread_obj in data.items():
                if not isinstance(thread_obj, dict):
                    continue
                thread_copy = dict(thread_obj)
                thread_copy.setdefault("id", legacy_id)
                thread_copy["__file_path"] = str(fp)
                thread_copy["__legacy_map_id"] = legacy_id
                records.append(thread_copy)
            continue

        # Single thread JSON format
        if isinstance(data, dict):
            thread_copy = dict(data)
            thread_copy["__file_path"] = str(fp)
            records.append(thread_copy)

    # Sort most recent first
    records.sort(key=lambda t: t.get("updated_at", t.get("timestamp", "")), reverse=True)
    return records


def delete_thread_file_record(thread_record: dict) -> None:
    """Delete thread record from its JSON file storage."""
    file_path = thread_record.get("__file_path")
    if not file_path:
        return
    fp = Path(file_path)
    if not fp.exists():
        return

    legacy_id = thread_record.get("__legacy_map_id")
    if legacy_id:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and legacy_id in data:
            del data[legacy_id]
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        return

    # Per-thread file format
    fp.unlink(missing_ok=True)


def export_all_threads_markdown(threads: list[dict]) -> str:
    """Build markdown export for all threads."""
    parts = ["# Research Threads Export", ""]
    for idx, thread in enumerate(threads, start=1):
        queries = thread.get("queries", []) or []
        title = thread.get("title", f"Thread {idx}")
        parts.append(f"## {idx}. {title}")
        parts.append(f"- Updated: {thread.get('updated_at', 'Unknown')}")
        parts.append(f"- Queries: {len(queries)}")
        parts.append("")
        for q_i, q in enumerate(queries, start=1):
            parts.append(f"### Query {q_i}")
            parts.append(f"**Question:** {q.get('query', '')}")
            parts.append("")
            parts.append("**Answer:**")
            parts.append(q.get("answer", ""))
            parts.append("")
            cits = q.get("citations", []) or []
            if cits:
                parts.append("**Citations:**")
                for c in cits:
                    parts.append(f"- [{c.get('source_id', 'Unknown')}, {c.get('chunk_id', 'Unknown')}]")
            parts.append("")
    return "\n".join(parts)


@st.cache_data
def load_source_manifest() -> list[dict]:
    """Load sources from data manifest and enrich with chunk stats/previews."""
    project_root = Path(__file__).resolve().parents[2]
    manifest_path = project_root / "data" / "data_manifest.csv"
    if not manifest_path.exists():
        return []

    sources = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed_rel = row.get("processed_path", "")
            processed_path = project_root / processed_rel if processed_rel else None
            chunk_count = 0
            chunk_previews = []
            authors = row.get("authors", "").strip()
            if processed_path and processed_path.exists():
                try:
                    with open(processed_path, "r", encoding="utf-8") as pf:
                        processed = json.load(pf)
                    chunk_count = int(
                        processed.get("statistics", {}).get("total_chunks", len(processed.get("chunks", [])))
                    )
                    for chunk in processed.get("chunks", [])[:5]:
                        text = str(chunk.get("text", "")).replace("\n", " ").strip()
                        if text:
                            chunk_previews.append(text[:220] + ("..." if len(text) > 220 else ""))
                    # Use pdf_metadata.author when manifest has "Research Team" or empty
                    if not authors or authors == "Research Team":
                        pdf_author = processed.get("pdf_metadata", {}).get("author", "")
                        if pdf_author:
                            parts = [p.strip() for p in str(pdf_author).split(";") if p.strip()]
                            if len(parts) <= 3:
                                authors = ", ".join(parts)
                            else:
                                authors = ", ".join(parts[:2]) + " et al."
                except Exception:
                    chunk_count = 0
                    chunk_previews = []

            year_raw = row.get("year", "")
            try:
                year_val = int(year_raw)
            except Exception:
                year_val = 0

            sources.append(
                {
                    "source_id": row.get("source_id", ""),
                    "title": row.get("title", ""),
                    "authors": authors or "Unknown authors",
                    "year": year_raw,
                    "year_int": year_val,
                    "source_type": row.get("source_type", ""),
                    "venue": row.get("venue", ""),
                    "url_or_doi": row.get("url_or_doi", ""),
                    "relevance_note": row.get("relevance_note", ""),
                    "chunk_count": chunk_count,
                    "chunk_previews": chunk_previews,
                }
            )
    return sources


def nav_button(label: str, page_key: str) -> bool:
    is_active = st.session_state.get("current_page") == page_key
    if st.sidebar.button(
        label,
        key=f"nav_{page_key}",
        type="primary" if is_active else "secondary",
        width="stretch",
    ):
        st.session_state.current_page = page_key
        st.rerun()
    return is_active


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 1.2rem 0.7rem 1rem 0.7rem;">
                <div style="font-size: 18px; font-weight: 600; color: #FFFFFF;">◆ AG RESEARCH PORTAL</div>
                <div style="height: 1px; background: rgba(255,255,255,0.1); margin-top: 0.75rem;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='font-size:11px; text-transform:uppercase; color:rgba(255,255,255,0.35); padding:0.5rem 0.7rem;'>Research</div>", unsafe_allow_html=True)
        nav_button("Search & Ask", PAGE_SEARCH_ASK)
        nav_button("Evidence Explorer", PAGE_EVIDENCE_EXPLORER)
        nav_button("Artifact Generator", PAGE_ARTIFACT_GENERATOR)
        st.markdown("<div style='font-size:11px; text-transform:uppercase; color:rgba(255,255,255,0.35); padding:1rem 0.7rem 0.5rem 0.7rem;'>System</div>", unsafe_allow_html=True)
        nav_button("Evaluation Dashboard", PAGE_EVALUATION_DASHBOARD)
        nav_button("Source Library", PAGE_SOURCE_LIBRARY)
        nav_button("Research Threads", PAGE_RESEARCH_THREADS)
        st.markdown("<div style='font-size:11px; text-transform:uppercase; color:rgba(255,255,255,0.35); padding:1rem 0.7rem 0.5rem 0.7rem;'>Export</div>", unsafe_allow_html=True)
        nav_button("Export Center", PAGE_EXPORT_CENTER)
        st.markdown("<div style='font-size:11px; text-transform:uppercase; color:rgba(255,255,255,0.35); padding:1rem 0.7rem 0.5rem 0.7rem;'>Tools</div>", unsafe_allow_html=True)
        if st.sidebar.button("Reload pipeline", key="reload_pipeline", help="Clear cache and reload RAG pipeline (use if retrieval shows NO EVIDENCE)"):
            load_pipeline.clear()
            st.session_state.search_result = None
            st.rerun()


def search_ask_page() -> None:
    st.markdown("## Research Query")
    st.markdown("Ask a research question to retrieve evidence from your corpus.")

    if "query_input" not in st.session_state:
        st.session_state.query_input = ""
    if "search_result" not in st.session_state:
        st.session_state.search_result = None
    if "thread_manager" not in st.session_state:
        st.session_state.thread_manager = get_thread_manager()
    if "selected_thread_id" not in st.session_state:
        st.session_state.selected_thread_id = None
    if "prefilled_query" in st.session_state and st.session_state.prefilled_query:
        st.session_state.query_input = st.session_state.prefilled_query
        st.session_state.prefilled_query = ""

    with st.form("search_form", clear_on_submit=False):
        input_col, ask_col = st.columns([5, 1])
        with input_col:
            query = st.text_input(
                "Enter your research question...",
                key="query_input",
                label_visibility="collapsed",
                placeholder="What are the advantages of small language models?",
            )
        with ask_col:
            st.markdown("<br>", unsafe_allow_html=True)
            ask_clicked = st.form_submit_button("Ask", type="primary")

        with st.expander("Retrieval Filters"):
            f1, f2, f3 = st.columns(3)
            with f1:
                year_range = st.slider("Year range", min_value=2018, max_value=2026, value=(2018, 2026))
            with f2:
                source_type = st.selectbox("Source type", options=["All", "peer-reviewed", "technical-report", "preprint"])
            with f3:
                max_sources = st.selectbox("Max sources", options=[5, 10, 15], index=1)

    should_run = ask_clicked or (query and st.session_state.get("prefill_run_once", False))
    if should_run:
        q = (query or st.session_state.get("query_input", "") or "").strip()
        if not q:
            render_status_strip("warning", "NO QUERY", "Enter a research question first.")
        else:
            st.session_state.search_result = None
            n_sources = len(load_source_manifest()) or 15
            with st.spinner(f"Retrieving evidence from {n_sources} sources..."):
                pipeline = load_pipeline()
                selected_types = None if source_type == "All" else [source_type]
                result = pipeline.query(
                    question=q,
                    k=int(max_sources),
                    similarity_threshold=STRICT_SIMILARITY_THRESHOLD,
                    year_min=year_range[0],
                    year_max=year_range[1],
                    source_types=selected_types,
                )
                result["query"] = q
                result.setdefault("metadata", {})
                result["metadata"]["retrieval_mode"] = "standard"
                result["metadata"]["retrieval_detail"] = "Semantic search"
                # Normalize bare citations in answer before storing (belt-and-suspenders with generator)
                if result.get("answer"):
                    result["answer"] = _normalize_bare_citations(result["answer"])
                st.session_state.search_result = result
                st.session_state.prefill_run_once = False

    sources = load_source_manifest()
    if not sources:
        render_status_strip(
            "info",
            "NOT INDEXED",
            "No sources have been indexed yet. Add sources to data/raw/ and run the ingestion pipeline.",
        )
        return

    result = st.session_state.search_result
    if not result:
        render_empty_state(
            "Enter a research question above to retrieve evidence from your corpus.",
            "Try: What are the advantages of small language models?",
        )
        return

    answer = result.get("answer", "")
    chunks = sorted(result.get("chunks", []), key=lambda c: float(c.get("similarity_score", 0)), reverse=True)
    citations = result.get("citations", [])

    render_retrieval_disclosure("standard", "Semantic search")

    if not chunks:
        render_status_strip(
            "warning",
            "NO EVIDENCE",
            "No relevant evidence found in the corpus for this query. Consider rephrasing or broadening your search terms.",
        )
        return

    valid_source_ids = {s.get("source_id", "") for s in load_source_manifest() if s.get("source_id")}
    valid_source_ids |= {c.get("source_id", "") for c in chunks}
    answer_clean, had_fabricated = _validate_citations_in_answer(answer, valid_source_ids)
    answer_clean = _normalize_bare_citations(answer_clean)
    # Use only valid citations for status (fabricated ones were stripped from answer)
    valid_citations = [c for c in citations if c.get("source_id", "") in valid_source_ids]
    valid_count = len(valid_citations)
    citation_strength = _confidence_from_citations(valid_count)
    # Partial warning: show when answer has multiple sentences but few citations, or single citation with substantial answer (suggests uncited/weakly supported claims)
    multi_sentence = answer_clean.count(". ") + answer_clean.count(".\n") >= 2
    single_citation_long_answer = valid_count == 1 and len(answer_clean) > 50
    partial_msg = "Some claims in this answer may not be fully supported by the corpus. Claims without citations should be verified independently." if (multi_sentence and valid_count < 2) or single_citation_long_answer else None
    render_answer_panel(answer_clean, partial_warning=partial_msg, fabricated_warning=had_fabricated)

    # Contradictory: answer says "not provided" / "not in excerpts" but cites chunks—lower confidence
    neg_phrases = ("not provided", "not in the excerpts", "not in the given excerpts", "does not mention", "does not contain", "insufficient information", "not directly provided")
    answer_lower = answer_clean.lower()
    says_missing = any(p in answer_lower for p in neg_phrases)
    if had_fabricated and valid_count > 0:
        render_status_strip("warning", "PARTIALLY GROUNDED", f"{valid_count} valid source{'s' if valid_count != 1 else ''} cited · Some citations were removed (not in corpus)")
    elif valid_count > 0 and says_missing:
        render_status_strip("warning", "PARTIALLY GROUNDED", f"{valid_count} source{'s' if valid_count != 1 else ''} cited · Verify: answer claims info is missing but cited chunks may contain it")
    elif valid_count > 0:
        render_status_strip("success", "GROUNDED", f"{valid_count} source{'s' if valid_count != 1 else ''} cited · Citation strength (count): {citation_strength}")
    else:
        render_status_strip("warning", "NOT GROUNDED", "Claims without citations should be verified independently.")

    display_query = result.get("query", "")
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("Save Thread", width="stretch"):
            manager = st.session_state.thread_manager
            thread_id = manager.create_thread(title=display_query[:100], description="Saved from Search & Ask")
            manager.add_query_to_thread(
                thread_id=thread_id,
                query=display_query,
                answer=answer_clean,
                citations=valid_citations,
                chunks=chunks,
                metadata=result.get("metadata", {}),
            )
            st.session_state.selected_thread_id = thread_id
            render_status_strip("success", "SAVED", "Query, answer, and evidence saved to Research Threads.")
    with a2:
        if st.button("Generate Artifact", width="stretch"):
            evidence_ids = [f"{c.get('source_id','Unknown')}:{c.get('chunk_id','Unknown')}" for c in chunks]
            st.session_state.artifact_prefill_query = display_query
            st.session_state.artifact_prefill_evidence_ids = evidence_ids
            st.session_state.last_query = display_query
            st.session_state.last_evidence_ids = evidence_ids
            st.session_state.current_page = PAGE_ARTIFACT_GENERATOR
            st.rerun()
    with a3:
        if st.button("Copy Answer", width="stretch"):
            st.session_state.copy_buffer = answer_clean
            render_status_strip("info", "COPY READY", "Answer prepared below for quick copy.")
            st.text_area("Answer text", value=answer_clean, height=180)

    st.markdown("### Retrieved Evidence")
    st.markdown(
        '<div style="font-size:20px; line-height:1.5; color:#525D6A; margin-bottom:1rem;">'
        "Match citations in the answer (e.g. Phi3_2024, Phi3_2024_chunk_0001) to the source_id · chunk_id in each card. "
        'Cards marked <strong>CITED IN ANSWER</strong> support specific claims above.</div>',
        unsafe_allow_html=True,
    )
    # Reorder: cited chunks first (in citation order), then uncited by relevance; use valid citations only
    cited_keys = {(c.get("source_id", ""), c.get("chunk_id", "")) for c in valid_citations}
    cited_order = [(c.get("source_id", ""), c.get("chunk_id", "")) for c in valid_citations]
    chunk_by_key = {(c.get("source_id", ""), c.get("chunk_id", "")): c for c in chunks}
    cited_chunks = [chunk_by_key[k] for k in cited_order if k in chunk_by_key]
    uncited_chunks = [c for c in chunks if (c.get("source_id", ""), c.get("chunk_id", "")) not in cited_keys]
    ordered_chunks = cited_chunks + uncited_chunks
    for chunk in ordered_chunks:
        key = (chunk.get("source_id", ""), chunk.get("chunk_id", ""))
        render_evidence_card(chunk, is_cited=key in cited_keys)


def evidence_explorer_page() -> None:
    st.markdown("## Evidence Explorer")
    render_empty_state(
        "No evidence retrieved yet. Start by asking a question on the Search & Ask page.",
        "",
    )


def _artifact_storage_dir() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    storage_dir = project_root / "outputs" / "artifacts"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def _save_artifact_to_disk(artifact_type: str, content: str | list, ext: str) -> Path:
    """Save generated artifact to outputs/artifacts/ and return path."""
    storage_dir = _artifact_storage_dir()
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    slug = artifact_type.lower().replace(" ", "_")
    fname = f"{slug}_{ts}.{ext}"
    path = storage_dir / fname
    if isinstance(content, list):
        import csv
        if ext == "csv" and content:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=content[0].keys())
                writer.writeheader()
                writer.writerows(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _inject_memo_font_size(html_str: str) -> str:
    """Add inline font-size: 19px to block elements; 22px for h4. Wrap bare text between h4s in <p>."""
    body_style = 'font-size: 19px !important;'
    heading_style = 'font-size: 22px !important;'

    def _wrap_block(m: re.Match) -> str:
        block = m.group(1)
        if not block.strip():
            return m.group(0)
        paras = re.split(r'\n\s*\n', block)
        wrapped = "".join(
            f'<p style="{body_style}">{p.strip()}</p>\n' for p in paras if p.strip()
        )
        return "</h4>\n" + wrapped

    # Wrap text between </h4> and next <h4> (or end) in <p> - preserves inline <span class="citation">
    html_str = re.sub(
        r"</h4>\s*([\s\S]*?)(?=<h4(?:\s|>)|\Z)", _wrap_block, html_str
    )
    # Also wrap any text before the first <h4>
    html_str = re.sub(
        r"\A([\s\S]*?)(?=<h4(?:\s|>))",
        lambda m: (
            "".join(
                f'<p style="{body_style}">{p.strip()}</p>\n'
                for p in re.split(r"\n\s*\n", m.group(1))
                if p.strip()
            )
            if m.group(1).strip()
            else m.group(0)
        ),
        html_str,
    )

    def _add(m: re.Match, style: str) -> str:
        s = m.group(0)
        if 'style="' in s or "style='" in s:
            s = re.sub(r'style=(["\'])([^"\']*)\1', rf'style=\1\2; {style}\1', s)
        else:
            s = s[:-1] + f' style="{style}">'
        return s

    for tag in ("p", "div", "li"):
        html_str = re.sub(rf"<{tag}(?:\s[^>]*)?>", lambda m: _add(m, body_style), html_str)
    html_str = re.sub(r"<h4(?:\s[^>]*)?>", lambda m: _add(m, heading_style), html_str)
    return html_str


def _save_generated_artifact(result: dict, project_root: Path) -> None:
    """Auto-save generated artifact to outputs/artifacts/."""
    try:
        if result["type"] == "evidence_table":
            p = _save_artifact_to_disk("evidence_table", result["data"], "csv")
            result["_saved_path"] = str(p.relative_to(project_root))
        elif result["type"] == "annotated_bib":
            md = _bib_to_markdown(result["data"])
            p = _save_artifact_to_disk("annotated_bib", md, "md")
            result["_saved_path"] = str(p.relative_to(project_root))
        else:
            p = _save_artifact_to_disk("synthesis_memo", result["data"], "md")
            result["_saved_path"] = str(p.relative_to(project_root))
    except Exception:
        pass


def artifact_generator_page() -> None:
    st.markdown("## Artifact Generator")
    st.caption("Generate structured research artifacts from your evidence.")

    project_root = Path(__file__).resolve().parents[2]
    chunks_metadata_path = project_root / "outputs" / "embeddings" / "chunks_metadata.json"
    sources = load_source_manifest()
    source_ids = sorted({s.get("source_id", "") for s in sources if s.get("source_id")})

    # Pre-fill from Search & Ask (support both spec keys and current keys)
    prefill_query = (
        st.session_state.get("artifact_prefill_query")
        or st.session_state.get("last_query")
        or ""
    )
    prefill_ids = (
        st.session_state.get("artifact_prefill_evidence_ids")
        or st.session_state.get("last_evidence_ids")
        or []
    )

    if prefill_query:
        st.caption(f'Based on your query: "{prefill_query[:80]}{"..." if len(prefill_query) > 80 else ""}"')

    # Configuration panel (form so Generate Artifact gets same styling as Ask button)
    st.markdown('<div class="dashboard-widget">', unsafe_allow_html=True)
    st.markdown('<div class="widget-title">Artifact Type</div>', unsafe_allow_html=True)

    with st.form("artifact_form", clear_on_submit=False):
        artifact_type = st.radio(
            "Artifact type",
            options=["Evidence Table", "Annotated Bibliography", "Synthesis Memo"],
            key="artifact_type_radio",
            label_visibility="collapsed",
        )
        type_descriptions = {
            "Evidence Table": "A table with Claim | Evidence Snippet | Citation | Confidence | Notes.",
            "Annotated Bibliography": "Source cards with Title, Key Claim, Method, Limitations, Why it matters.",
            "Synthesis Memo": "800–1200 word memo with inline citations and References section.",
        }
        st.caption(type_descriptions[artifact_type])

        research_question = st.text_input(
            "Research question",
            value=prefill_query,
            placeholder="Enter your research question...",
            key="artifact_research_question",
        )

        source_scope_options = ["All"] + source_ids
        selected_sources = st.multiselect(
            "Source scope",
            options=source_scope_options,
            default=["All"],
            key="artifact_source_scope",
        )
        if "All" in selected_sources or not selected_sources:
            source_filter = None
        else:
            source_filter = set(selected_sources)

        max_entries = st.selectbox(
            "Max entries",
            options=[5, 10, 15, 20],
            index=1,
            key="artifact_max_entries",
        )

        generate_clicked = st.form_submit_button("Generate Artifact", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)

    # Initialize artifact result in session state
    if "artifact_result" not in st.session_state:
        st.session_state.artifact_result = None

    if generate_clicked:
        if not research_question.strip():
            render_status_strip("warning", "NO QUERY", "Enter a research question first.")
        else:
            with st.spinner(f"Generating {artifact_type.lower()}... analyzing sources"):
                chunks = []
                if prefill_ids:
                    chunks = load_chunks_by_evidence_ids(prefill_ids, chunks_metadata_path)
                if not chunks:
                    pipeline = load_pipeline()
                    result = pipeline.query(
                        question=research_question.strip(),
                        k=int(max_entries),
                        similarity_threshold=STRICT_SIMILARITY_THRESHOLD,
                    )
                    chunks = result.get("chunks", [])
                if source_filter:
                    chunks = [c for c in chunks if c.get("source_id") in source_filter]
                chunks = chunks[: int(max_entries)]

                if not chunks:
                    render_status_strip(
                        "warning",
                        "NO EVIDENCE",
                        "No relevant chunks found. Try a different question or broaden source scope.",
                    )
                else:
                    if artifact_type == "Evidence Table":
                        table_rows = generate_evidence_table_from_chunks(
                            research_question, chunks, int(max_entries)
                        )
                        st.session_state.artifact_result = {
                            "type": "evidence_table",
                            "data": table_rows,
                            "query": research_question,
                        }
                    elif artifact_type == "Annotated Bibliography":
                        bib_entries = generate_annotated_bib_from_chunks(
                            research_question, chunks, int(max_entries)
                        )
                        st.session_state.artifact_result = {
                            "type": "annotated_bib",
                            "data": bib_entries,
                            "query": research_question,
                        }
                    else:
                        memo_text = generate_synthesis_memo_with_llm(
                            research_question, chunks, int(max_entries)
                        )
                        st.session_state.artifact_result = {
                            "type": "synthesis_memo",
                            "data": memo_text,
                            "query": research_question,
                        }
                    # Auto-save to outputs/artifacts/
                    _save_generated_artifact(st.session_state.artifact_result, project_root)
                    st.rerun()

    result = st.session_state.artifact_result
    if not result:
        render_empty_state(
            "Select an artifact type and enter a research question to generate your first research artifact.",
            "",
        )
        return

    # Render generated artifact
    st.markdown("### Generated Artifact")
    if result["type"] == "evidence_table":
        export_data = result["data"]
        _render_evidence_table_html(export_data)
        csv_content = _table_to_csv(export_data)
        md_content = _table_to_markdown(export_data)
    elif result["type"] == "annotated_bib":
        for entry in result["data"]:
            import html as html_mod
            tl = html_mod.escape(str(entry.get("title_line", "")))
            kc = html_mod.escape(str(entry.get("key_claim", "")))
            mt = html_mod.escape(str(entry.get("method", "")))
            lm = html_mod.escape(str(entry.get("limitations", "")))
            wm = html_mod.escape(str(entry.get("why_it_matters", entry.get("relevance", ""))))
            st.markdown(
                f"""
                <div class="thread-card" style="margin-bottom: 1rem;">
                    <div class="thread-title" style="font-size: 17px; margin-bottom: 0.5rem;">{tl}</div>
                    <div style="font-size: 20px; color: #1A1F26; margin-bottom: 0.4rem;"><strong>Key Claim:</strong> {kc}</div>
                    <div style="font-size: 20px; color: #1A1F26; margin-bottom: 0.4rem;"><strong>Method:</strong> {mt}</div>
                    <div style="font-size: 20px; color: #525D6A; margin-bottom: 0.4rem;"><strong>Limitations:</strong> {lm}</div>
                    <div style="font-size: 20px; color: #525D6A; font-style: italic;"><strong>Why it matters:</strong> {wm}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        export_data = result["data"]
        csv_content = None
        md_content = _bib_to_markdown(export_data)
    else:
        memo_html = render_citations(result["data"])
        memo_html = _inject_memo_font_size(memo_html)
        st.markdown(
            f'<div class="executive-summary" style="font-size: 19px !important; line-height: 1.6 !important;">{memo_html}</div>',
            unsafe_allow_html=True,
        )
        export_data = result["data"]
        csv_content = None
        md_content = result["data"]

    # Export row (only after generation)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Export")
    c1, c2, c3 = st.columns(3)
    with c1:
        if csv_content is not None:
            st.download_button(
                "Download CSV",
                data=csv_content,
                file_name=f"evidence_table_{_timestamp_slug()}.csv",
                mime="text/csv",
                key="artifact_export_csv",
            )
        else:
            st.button("Download CSV", key="artifact_csv_disabled", disabled=True)
    with c2:
        if md_content:
            st.download_button(
                "Download Markdown",
                data=md_content,
                file_name=f"artifact_{_timestamp_slug()}.md",
                mime="text/markdown",
                key="artifact_export_md",
            )
    with c3:
        artifact_type_display = (
            "Evidence Table" if result["type"] == "evidence_table"
            else "Annotated Bibliography" if result["type"] == "annotated_bib"
            else "Synthesis Memo"
        )
        if result["type"] == "evidence_table":
            pdf_content_rows = export_data
        elif result["type"] == "annotated_bib":
            pdf_content_rows = export_data
        else:
            pdf_content_rows = [{"Memo": export_data}]
        title = research_question[:60] + ("..." if len(research_question) > 60 else "")
        pdf_bytes = _generate_artifact_pdf(title, pdf_content_rows, artifact_type_display)
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"{artifact_type_display.lower().replace(' ', '_')}_{_timestamp_slug()}.pdf",
            mime="application/pdf",
            key="artifact_export_pdf",
        )

    if result.get("_saved_path"):
        st.caption(f"Saved to {result['_saved_path']}")


def _timestamp_slug() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _render_evidence_table_html(rows: list) -> None:
    """Render evidence table as readable HTML with word-wrap and confidence colors."""
    if not rows:
        return
    confidence_colors = {"High": "#0D9668", "Medium": "#D49717", "Low": "#CC3333"}
    headers = ["Claim", "Evidence Snippet", "Citation", "Confidence", "Notes"]
    table_rows = []
    for r in rows:
        conf = str(r.get("Confidence", ""))
        conf_color = confidence_colors.get(conf, "#1A1F26")
        conf_cell = f'<span style="color:{conf_color}; font-weight:600;">{html.escape(conf)}</span>'
        citation = str(r.get("Citation", ""))
        citation_cell = f'<span class="citation">{html.escape(citation)}</span>' if citation else ""
        table_rows.append([
            str(r.get("Claim", "")),
            str(r.get("Evidence Snippet", "")),
            citation_cell,
            conf_cell,
            str(r.get("Notes", "")),
        ])
    html_out = build_report_table(
        headers=headers,
        rows=table_rows,
        col_types=["medium", "long", "short", "short", "medium"],
        raw_html_cells=True,
        theme="evidence",
    )
    st.html(
        f'<div class="evidence-table-wrapper" style="font-size:20px !important; line-height:1.5 !important;">{html_out}</div>'
    )


def _table_to_csv(rows: list) -> str:
    import io
    import csv
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return buf.getvalue()


def _table_to_markdown(rows: list) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(h, ""))[:100] for h in headers) + " |")
    return "\n".join(lines)


def _bib_to_markdown(entries: list) -> str:
    lines = ["# Annotated Bibliography", ""]
    for e in entries:
        lines.append(f"## {e.get('title_line', '')}")
        lines.append("")
        lines.append(f"**Key Claim:** {e.get('key_claim', '')}")
        lines.append(f"**Method:** {e.get('method', '')}")
        lines.append(f"**Limitations:** {e.get('limitations', '')}")
        lines.append(f"**Why it matters:** {e.get('why_it_matters', e.get('relevance', ''))}")
        lines.append("")
    return "\n".join(lines)


def _sanitize_for_pdf(text: str) -> str:
    """Sanitize text for PDF: Helvetica only supports Latin-1; replace/skip other chars."""
    import re
    import unicodedata
    out = str(text)
    # Strip HTML tags (e.g. <h4>Executive Summary</h4> -> Executive Summary)
    out = re.sub(r"<[^>]+>", "", out)
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...",
    }
    for k, v in replacements.items():
        out = out.replace(k, v)
    out = unicodedata.normalize("NFKD", out).encode("ascii", "replace").decode("ascii")
    return out


def _generate_artifact_pdf(title: str, content_rows: list, artifact_type: str) -> bytes:
    """Generate PDF bytes for artifact export. Requires fpdf2 in requirements.txt."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 43, 70)
    pdf.cell(0, 12, _sanitize_for_pdf(title[:80]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    if artifact_type == "Evidence Table":
        headers = ["Claim", "Evidence Snippet", "Citation", "Confidence", "Notes"]
        col_types = ["medium", "long", "id", "short", "medium"]
        rows = [
            [_sanitize_for_pdf(str(r.get(h, ""))) for h in headers]
            for r in content_rows
        ]
        table_to_pdf(pdf, headers, rows, col_types)
    else:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(26, 31, 38)
        bib_labels = {"title_line": "Source", "key_claim": "Key Claim", "method": "Method", "limitations": "Limitations", "why_it_matters": "Why it matters"}
        for row in content_rows:
            for key, value in row.items():
                label = bib_labels.get(key, key.replace("_", " ").title()) if artifact_type == "Annotated Bibliography" else str(key)
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 7, _sanitize_for_pdf(label) + ":", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 11)
                val_str = _sanitize_for_pdf(str(value))
                max_len = 500 if key != "Memo" else len(val_str)
                pdf.multi_cell(0, 6, val_str[:max_len])
                pdf.ln(3)
            pdf.ln(4)

    return bytes(pdf.output())


def _eval_runs_dir() -> Path:
    """Return logs/eval_runs directory, creating if needed."""
    project_root = Path(__file__).resolve().parents[2]
    d = project_root / "logs" / "eval_runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_latest_eval_results() -> dict | None:
    """Load most recent eval from logs/eval_runs/ or outputs/. Normalizes schema."""
    project_root = Path(__file__).resolve().parents[2]

    def _load(path: Path) -> dict | None:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def _normalize(data: dict) -> dict:
        """Normalize to {aggregate, results} for dashboard consumption."""
        agg = data.get("aggregate") or data.get("aggregate_metrics")
        res = data.get("results") or data.get("individual_results") or []
        return {"aggregate": agg, "results": res}

    # Prefer logs/eval_runs (app format)
    runs_dir = project_root / "logs" / "eval_runs"
    if runs_dir.exists():
        files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            raw = _load(files[0])
            if raw and (raw.get("aggregate") or raw.get("aggregate_metrics")):
                return _normalize(raw)

    # Fallback: outputs/evaluation_results_*.json (standalone run_evaluation format)
    outputs = project_root / "outputs"
    if outputs.exists():
        files = sorted(outputs.glob("evaluation_results_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            raw = _load(files[0])
            if raw and (raw.get("aggregate_metrics") or raw.get("individual_results") is not None):
                return _normalize(raw)
    return None


def _derive_failure_cases(results: list[dict], aggregate: dict) -> list[dict]:
    """Derive 3+ representative failure cases from evaluation results."""
    successful = [r for r in results if r.get("success") and r.get("metrics")]
    if not successful:
        return []

    def _score(r: dict) -> float:
        m = r.get("metrics", {})
        g = m.get("groundedness", {})
        a = m.get("answer_relevance", {})
        cd = g.get("citation_density", 0)
        has_cit = g.get("has_citations", 0)
        tc = a.get("term_coverage", 0)
        ls = a.get("length_score", 0)
        # Composite: prefer low scores
        grounded = min(1.0, cd * 2) if has_cit else 0.0
        relevance = (tc + ls) / 2
        return (grounded + relevance) / 2

    # Sort by score ascending (worst first)
    ranked = sorted(successful, key=_score)
    failures = []
    for r in ranked[:8]:  # Consider up to 8 candidates
        s = _score(r)
        if s >= 0.7:
            break
        m = r.get("metrics", {})
        g = m.get("groundedness", {})
        a = m.get("answer_relevance", {})
        citation_count = g.get("citation_count", 0)
        citation_density = g.get("citation_density", 0)
        term_coverage = a.get("term_coverage", 0)
        length_score = a.get("length_score", 0)

        if citation_count == 0:
            tag = "MISSING EVIDENCE"
        elif citation_density >= 0.5 and term_coverage < 0.4:
            tag = "WRONG CITATION"
        elif length_score > 0.7 and citation_density < 0.3:
            tag = "OVERCONFIDENT"
        else:
            tag = "HALLUCINATION"

        what_wrong = ""
        if tag == "MISSING EVIDENCE":
            what_wrong = "Answer was generated without citing any retrieved evidence."
        elif tag == "WRONG CITATION":
            what_wrong = "Answer cites sources but content does not align with query terms."
        elif tag == "OVERCONFIDENT":
            what_wrong = "Answer is lengthy but poorly grounded in citations."
        else:
            what_wrong = "Answer may contain claims not supported by retrieved evidence."

        retrieved_preview = ""
        chunks = r.get("retrieved_chunks", [])[:2]
        for c in chunks:
            retrieved_preview += (c.get("text_preview", "") or "")[:200] + " ... "
        answer_preview = (r.get("answer") or "")[:300] + ("..." if len(r.get("answer", "")) > 300 else "")

        suggested = "Improve retrieval relevance or add verification step."
        if tag == "MISSING EVIDENCE":
            suggested = "Lower similarity threshold or expand retrieval scope."
        elif tag == "WRONG CITATION":
            suggested = "Add chunk-answer alignment check before citation."
        elif tag == "OVERCONFIDENT":
            suggested = "Enforce citation requirements in the generation prompt."

        failures.append({
            "query": r.get("query", ""),
            "tag": tag,
            "what_wrong": what_wrong,
            "retrieved_preview": retrieved_preview.strip() or "(no chunks)",
            "answer_preview": answer_preview,
            "suggested_fix": suggested,
            "result": r,
        })
        if len(failures) >= 5:
            break

    return failures[:5]  # Cap at 5


def evaluation_dashboard_page() -> None:
    st.markdown("## Evaluation Dashboard")

    project_root = Path(__file__).resolve().parents[2]
    query_set_path = project_root / "src" / "eval" / "query_set.json"

    # Initialize session state for eval results
    if "eval_results" not in st.session_state:
        st.session_state.eval_results = _load_latest_eval_results()

    run_clicked = False
    if not st.session_state.eval_results:
        render_empty_state(
            "No evaluation runs yet. Click 'Run Evaluation' to assess your system's performance.",
            "",
        )
        run_clicked = st.button("Run Evaluation", type="primary", key="eval_run_btn")
    else:
        run_clicked = st.button("Run Evaluation", key="eval_rerun_btn")

    if run_clicked:
        import os
        from datetime import datetime

        if not os.getenv("OPENAI_API_KEY"):
            render_status_strip("warning", "NO API KEY", "Set OPENAI_API_KEY to run evaluation.")
        elif not query_set_path.exists():
            render_status_strip("warning", "NO QUERY SET", f"Query set not found: {query_set_path}")
        else:
            with open(query_set_path, "r") as f:
                query_set = json.load(f)
            queries = query_set.get("queries", [])
            pipeline = load_pipeline()
            from eval.run_evaluation import evaluate_query, aggregate_metrics

            results = []
            total = len(queries)
            progress_placeholder = st.empty()
            for i, q in enumerate(queries, 1):
                progress_placeholder.progress(
                    i / total,
                    text=f"Running evaluation set... {i}/{total} queries complete",
                )
                r = evaluate_query(pipeline, q)
                results.append(r)

            aggregate = aggregate_metrics(results)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            runs_dir = _eval_runs_dir()
            out_path = runs_dir / f"eval_{timestamp}.json"
            payload = {
                "timestamp": timestamp,
                "aggregate": aggregate,
                "results": results,
            }
            with open(out_path, "w") as f:
                json.dump(payload, f, indent=2)

            st.session_state.eval_results = payload
            progress_placeholder.empty()
            st.rerun()

    data = st.session_state.eval_results
    if not data:
        return

    aggregate = data.get("aggregate", {})
    results = data.get("results", [])

    if aggregate.get("error"):
        render_status_strip("warning", "EVAL ERROR", aggregate["error"])
        return

    # Build per-query rows (same formula for aggregate and table: min(1.0, cd*2) when has_citations else 0, capped 0-1)
    g = aggregate.get("groundedness", {})
    rows = []
    for r in results:
        if not r.get("success") or not r.get("metrics"):
            rows.append({
                "Query": r.get("query", ""),
                "Type": r.get("query_type", ""),
                "Groundedness": 0.0,
                "Citation": 0.0,
                "Relevance": 0.0,
            })
        else:
            gm = r["metrics"].get("groundedness", {})
            am = r["metrics"].get("answer_relevance", {})
            cd = gm.get("citation_density", 0)
            has_cit = gm.get("has_citations", 0)
            grounded = min(1.0, cd * 2) if has_cit else 0.0
            citation_p = has_cit
            relevance = (am.get("term_coverage", 0) + am.get("length_score", 0)) / 2
            rows.append({
                "Query": r.get("query", ""),
                "Type": r.get("query_type", ""),
                "Groundedness": round(grounded, 2),
                "Citation": round(citation_p, 2),
                "Relevance": round(relevance, 2),
            })

    # Aggregate from rows (aligned with per-query formula)
    groundedness_val = sum(row["Groundedness"] for row in rows) / len(rows) if rows else 0
    relevance_val = sum(row["Relevance"] for row in rows) / len(rows) if rows else 0
    citation_precision_val = g.get("pct_with_citations", 0) / 100.0 if g.get("pct_with_citations") is not None else 0
    query_count = aggregate.get("total_queries", 0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card(groundedness_val, "Groundedness")
    with c2:
        render_metric_card(citation_precision_val, "Citation Precision")
    with c3:
        render_metric_card(relevance_val, "Relevance")
    with c4:
        render_metric_card(query_count, "Query Count", color_tone="green")

    # Per-Query Results
    st.markdown('<div class="widget-title">Per-Query Results</div>', unsafe_allow_html=True)
    sort_cols = ["Query", "Type", "Groundedness", "Citation", "Relevance"]
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        sort_col = st.selectbox(
            "Sort by",
            options=sort_cols,
            index=sort_cols.index(st.session_state.get("eval_sort_column", "Groundedness")),
            key="eval_sort_column",
        )
    with sc2:
        sort_asc = st.checkbox(
            "Ascending",
            value=st.session_state.get("eval_sort_ascending", True),
            key="eval_sort_ascending",
        )

    def _sort_key(row):
        val = row.get(sort_col, "")
        if isinstance(val, (int, float)):
            return (0, val)
        return (1, str(val).lower())

    sorted_rows = sorted(rows, key=_sort_key, reverse=not sort_asc)
    render_eval_results_table(sorted_rows)

    # Representative Failure Cases
    st.markdown('<div class="widget-title">Representative Failure Cases</div>', unsafe_allow_html=True)
    failures = _derive_failure_cases(results, aggregate)
    if not failures:
        st.caption("No significant failure cases identified (all queries scored above threshold).")
    else:
        for fc in failures:
            render_failure_card(
                query=fc["query"],
                tag=fc["tag"],
                what_wrong=fc["what_wrong"],
                retrieved_preview=fc["retrieved_preview"],
                answer_preview=fc["answer_preview"],
                suggested_fix=fc["suggested_fix"],
            )

    # Export Report
    def _build_export_md() -> str:
        lines = ["# Evaluation Report", ""]
        lines.append(f"- **Groundedness:** {groundedness_val:.2f}")
        lines.append(f"- **Citation Precision:** {citation_precision_val:.2f}")
        lines.append(f"- **Relevance:** {relevance_val:.2f}")
        lines.append(f"- **Query Count:** {query_count}")
        lines.append("")
        lines.append("## Per-Query Results")
        lines.append("")
        for row in rows:
            lines.append(f"- {row['Query']} | {row['Type']} | G:{row['Groundedness']} C:{row['Citation']} R:{row['Relevance']}")
        lines.append("")
        lines.append("## Failure Cases")
        lines.append("")
        for fc in failures:
            lines.append(f"### {fc['tag']}")
            lines.append(f"**Query:** {fc['query'][:100]}...")
            lines.append(f"**What went wrong:** {fc['what_wrong']}")
            lines.append(f"**Suggested fix:** {fc['suggested_fix']}")
            lines.append("")
        return "\n".join(lines)

    export_md = _build_export_md()
    st.download_button(
        "Export Report",
        data=export_md,
        file_name="evaluation_report.md",
        mime="text/markdown",
        key="eval_export_btn",
    )


def source_library_page() -> None:
    sources = load_source_manifest()
    total_sources = len(sources)
    total_chunks = sum(int(s.get("chunk_count", 0)) for s in sources)

    st.markdown(f"## Source Library ({total_sources} sources)")
    st.caption(f"{total_sources} sources · {total_chunks} chunks")

    if not sources:
        render_empty_state(
            "No sources indexed. Add PDFs or documents to data/raw/ and run the ingestion pipeline.",
            "",
        )
        return

    with st.expander("Filters"):
        f1, f2, f3 = st.columns(3)
        with f1:
            keyword = st.text_input("Search by keyword", value="", placeholder="Title, author, source ID...")
        with f2:
            source_types = sorted({s.get("source_type", "").strip() for s in sources if s.get("source_type", "").strip()})
            selected_type = st.selectbox("Filter by source type", options=["All"] + source_types)
        with f3:
            years = sorted({int(s.get("year_int", 0)) for s in sources if int(s.get("year_int", 0)) > 0}, reverse=True)
            selected_year = st.selectbox("Filter by year", options=["All"] + years)

    filtered = []
    key = keyword.strip().lower()
    for src in sources:
        haystack = " ".join(
            [
                str(src.get("source_id", "")),
                str(src.get("title", "")),
                str(src.get("authors", "")),
                str(src.get("venue", "")),
                str(src.get("relevance_note", "")),
            ]
        ).lower()
        if key and key not in haystack:
            continue
        if selected_type != "All" and src.get("source_type", "") != selected_type:
            continue
        if selected_year != "All" and int(src.get("year_int", 0)) != int(selected_year):
            continue
        filtered.append(src)

    filtered.sort(key=lambda s: (int(s.get("year_int", 0)), str(s.get("title", ""))), reverse=True)

    if not filtered:
        render_empty_state(
            "No sources match current filters.",
            "Try broadening keyword/type/year filters.",
        )
        return

    for src in filtered:
        render_source_card(src, key_prefix="source_lib")
        st.markdown("<br>", unsafe_allow_html=True)


def research_threads_page() -> None:
    st.markdown("## Research Threads")
    st.caption("Your saved research sessions.")

    threads = load_threads_from_json_files()
    if not threads:
        render_empty_state(
            "No saved threads yet. Use 'Save Thread' on the Search & Ask page after running a query.",
            "",
        )
        return

    for thread in threads:
        queries = thread.get("queries", []) or []
        latest = queries[-1] if queries else {}
        query_full = str(latest.get("query", thread.get("title", "Untitled query")))
        query_preview = query_full[:100] + ("..." if len(query_full) > 100 else "")
        timestamp = str(latest.get("timestamp", thread.get("updated_at", thread.get("created_at", "Unknown"))))
        sources_cited = len(latest.get("citations", []) or [])
        confidence = _confidence_from_citations(sources_cited)

        card_data = {
            "id": thread.get("id", "unknown"),
            "query_preview": query_preview,
            "timestamp_display": timestamp[:19],
            "sources_cited_count": sources_cited,
            "confidence_level": confidence,
        }
        actions = render_thread_card(card_data, key_prefix="threads")

        if actions["resume"]:
            st.session_state.prefilled_query = query_full
            st.session_state.prefill_run_once = True
            st.session_state.current_page = PAGE_SEARCH_ASK
            st.rerun()

        if actions["delete"]:
            delete_thread_file_record(thread)
            render_status_strip("success", "DELETED", "Thread removed.")
            st.rerun()

        if actions["view"]:
            st.session_state[f"thread_view_{thread.get('id', 'unknown')}"] = not st.session_state.get(
                f"thread_view_{thread.get('id', 'unknown')}", False
            )

        if st.session_state.get(f"thread_view_{thread.get('id', 'unknown')}", False):
            with st.expander("Thread Details", expanded=True):
                st.markdown("**Full Query**")
                st.markdown(query_full)
                st.markdown("**Full Answer**")
                full_answer = str(latest.get("answer", ""))
                st.markdown(render_citations(full_answer), unsafe_allow_html=True)

                chunk_list = latest.get("chunks", []) or []
                thread_citations = latest.get("citations", []) or []
                if chunk_list:
                    st.markdown("**Evidence Cards**")
                    cited_keys = {(c.get("source_id", ""), c.get("chunk_id", "")) for c in thread_citations}
                    cited_order = [(c.get("source_id", ""), c.get("chunk_id", "")) for c in thread_citations]
                    chunk_by_key = {(c.get("source_id", ""), c.get("chunk_id", "")): c for c in chunk_list}
                    cited_chunks = [chunk_by_key[k] for k in cited_order if k in chunk_by_key]
                    uncited_chunks = [c for c in chunk_list if (c.get("source_id", ""), c.get("chunk_id", "")) not in cited_keys]
                    ordered_chunks = cited_chunks + uncited_chunks
                    for chunk in ordered_chunks:
                        key = (chunk.get("source_id", ""), chunk.get("chunk_id", ""))
                        render_evidence_card(chunk, is_cited=key in cited_keys)

                artifacts = thread.get("artifacts", []) or latest.get("artifacts", []) or []
                st.markdown("**Artifacts**")
                if artifacts:
                    for artifact in artifacts:
                        st.markdown(f"- {artifact}")
                else:
                    st.caption("No artifacts generated from this thread yet.")

        st.markdown("<br>", unsafe_allow_html=True)

    export_md = export_all_threads_markdown(threads)
    st.download_button(
        "Export All Threads",
        data=export_md,
        file_name="all_threads_export.md",
        mime="text/markdown",
        width="stretch",
    )


def export_center_page() -> None:
    st.markdown("## Export Center")
    st.caption("Download research artifacts, evaluation reports, and thread exports.")

    project_root = Path(__file__).resolve().parents[2]
    dirs = [
        ("Research Artifacts", project_root / "outputs" / "artifacts"),
        ("Evaluation Reports", project_root / "logs" / "eval_runs"),
        ("Research Threads", project_root / "outputs" / "threads"),
    ]

    all_files: list[tuple[str, Path]] = []
    for section_name, dir_path in dirs:
        if dir_path.exists():
            for p in dir_path.iterdir():
                if p.is_file():
                    all_files.append((section_name, p))

    if not all_files:
        render_empty_state(
            "No exports available. Generate artifacts or run evaluations to create exportable files.",
            "",
        )
        return

    for section_name, dir_path in dirs:
        section_files = [p for name, p in all_files if name == section_name]
        section_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if not section_files:
            continue

        st.markdown(f'<div class="widget-title">{section_name}</div>', unsafe_allow_html=True)
        for i, fp in enumerate(section_files):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"`{fp.name}`")
            with col2:
                with open(fp, "rb") as f:
                    data = f.read()
                mime = "application/octet-stream"
                if fp.suffix in (".json",):
                    mime = "application/json"
                elif fp.suffix in (".csv",):
                    mime = "text/csv"
                elif fp.suffix in (".md", ".markdown"):
                    mime = "text/markdown"
                elif fp.suffix in (".pdf",):
                    mime = "application/pdf"
                st.download_button(
                    "Download",
                    data=data,
                    file_name=fp.name,
                    mime=mime,
                    type="secondary",
                    key=f"export_{section_name}_{i}_{fp.name}",
                )
        st.markdown("<br>", unsafe_allow_html=True)


def route_current_page() -> None:
    routes = {
        PAGE_SEARCH_ASK: search_ask_page,
        PAGE_EVIDENCE_EXPLORER: evidence_explorer_page,
        PAGE_ARTIFACT_GENERATOR: artifact_generator_page,
        PAGE_EVALUATION_DASHBOARD: evaluation_dashboard_page,
        PAGE_SOURCE_LIBRARY: source_library_page,
        PAGE_RESEARCH_THREADS: research_threads_page,
        PAGE_EXPORT_CENTER: export_center_page,
    }
    routes.get(st.session_state.get("current_page", PAGE_SEARCH_ASK), search_ask_page)()


def main() -> None:
    if "current_page" not in st.session_state:
        st.session_state.current_page = PAGE_SEARCH_ASK
    render_sidebar()
    route_current_page()


if __name__ == "__main__":
    main()

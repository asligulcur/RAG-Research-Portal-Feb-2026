"""Reusable UI components for AG Research Portal."""

import html
import re
import streamlit as st

from table_utils import build_report_table


def render_citations(text: str) -> str:
    """Replace citation patterns with styled citation chips."""
    if not text:
        return ""

    def _make_chip(label: str) -> str:
        return f'<span class="citation">{html.escape(label)}</span>'

    def _full_citation(sid: str, cid: str) -> str:
        return f"[Source: {sid}, Chunk: {cid}]"

    # Pattern 1: [Source: X, Chunk: Y] — preferred format
    pattern1 = r"\[Source:\s*([^,\]]+),\s*Chunk:\s*([^\]]+)\]"
    def _chip1(m: re.Match) -> str:
        return _make_chip(_full_citation(m.group(1).strip(), m.group(2).strip()))
    text = re.sub(pattern1, _chip1, text)

    # Pattern 2: [SourceID, ChunkID] — square brackets, no labels
    pattern2 = r"\[([A-Za-z0-9_]+),\s*([A-Za-z0-9_]+)\]"
    def _chip2(m: re.Match) -> str:
        return _make_chip(_full_citation(m.group(1).strip(), m.group(2).strip()))
    text = re.sub(pattern2, _chip2, text)

    # Pattern 3: (SourceID, ChunkID) — parentheses with full chunk id
    pattern3 = r"\(([A-Za-z0-9_]+),\s*([A-Za-z0-9_]+)\)"
    def _chip3(m: re.Match) -> str:
        return _make_chip(_full_citation(m.group(1).strip(), m.group(2).strip()))
    text = re.sub(pattern3, _chip3, text)

    # Pattern 4: (SourceID) or (SourceID, chunk_XX) — original spec format
    pattern4 = r"\((\w+(?:\d{4})(?:,\s*chunk_\d+)?)\)"
    def _chip4(m: re.Match) -> str:
        full = m.group(1)
        parts = full.split(",")
        sid = parts[0].strip()
        cid = parts[1].strip() if len(parts) > 1 else "chunk_00"
        return _make_chip(_full_citation(sid, cid))
    text = re.sub(pattern4, _chip4, text)

    # Pattern 5: bare "SourceID, ChunkID" — LLM sometimes omits brackets (source_id, source_id_chunk_NNNN)
    pattern5 = r"(\w+_\d{4}),\s*(\1_chunk_\d+)"
    def _chip5(m: re.Match) -> str:
        return _make_chip(_full_citation(m.group(1), m.group(2)))
    text = re.sub(pattern5, _chip5, text)

    return text


def render_answer_panel(answer_text: str, partial_warning: str | None = None, fabricated_warning: bool = False) -> None:
    """Render answer text inside executive summary panel with inline chips. Optionally append amber/red warnings."""
    rendered = render_citations(answer_text)
    warning_html = ""
    if fabricated_warning:
        warning_html += f'<div style="margin-top:1rem; padding:0.75rem; background:rgba(204,51,51,0.06); border-left:3px solid #CC3333; color:#CC3333; font-size:20px;">One or more citations were removed because they could not be resolved to a source in the corpus.</div>'
    if partial_warning:
        warning_html += f'<div style="margin-top:1rem; padding:0.75rem; background:rgba(212,151,23,0.08); border-left:3px solid #D49717; color:#A25B00; font-size:20px;">{html.escape(partial_warning)}</div>'
    st.markdown(f'<div class="executive-summary">{rendered}{warning_html}</div>', unsafe_allow_html=True)


def render_evidence_card(chunk_dict: dict, is_cited: bool = False) -> None:
    """Render one evidence card. If is_cited, show a badge so users can tie it to citations in the answer.
    Shows a short preview by default; use expander to see full excerpt (like Retrieval Filters)."""
    score = float(chunk_dict.get("similarity_score", chunk_dict.get("score", 0.0)))
    score_color = "#0D9668" if score > 0.8 else "#D49717" if score >= 0.5 else "#CC3333"

    source_id = html.escape(str(chunk_dict.get("source_id", "Unknown")))
    chunk_id = html.escape(str(chunk_dict.get("chunk_id", "chunk_00")))
    full_text = str(chunk_dict.get("text", "") or "").strip()
    snippet_len = 1500  # Full excerpt length when expanded
    preview_lines = 5   # Short preview: first 5 lines in main card

    if not full_text:
        preview = "(No text in this chunk)"
    else:
        lines = [ln.strip() for ln in full_text.split("\n")]
        # Skip leading junk (page numbers, single chars, fragments from PDF extraction)
        meaningful = [ln for ln in lines if len(ln) > 2 and not ln.isdigit()]
        if not meaningful:
            meaningful = lines[:preview_lines]  # fallback to raw
        preview = "\n".join(meaningful[:preview_lines])
        if len(meaningful) > preview_lines or len(lines) > preview_lines:
            preview += "\n..."

    md = chunk_dict.get("paper_metadata", chunk_dict.get("metadata", {}))
    authors = html.escape(str(md.get("authors", chunk_dict.get("authors", ""))))
    year = html.escape(str(md.get("year", chunk_dict.get("year", ""))))
    venue = html.escape(str(md.get("venue", chunk_dict.get("venue", ""))))
    source_type = html.escape(str(md.get("source_type", chunk_dict.get("source_type", ""))))

    cited_badge = '<span style="font-size:11px; font-weight:700; color:#0D9668; background:rgba(13,150,104,0.12); padding:2px 8px; border-radius:4px; margin-left:8px;">CITED IN ANSWER</span>' if is_cited else ""

    preview_escaped = html.escape(preview)

    st.markdown(
        f"""
        <div class="thread-card" style="margin-bottom: 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-family:'SF Mono','JetBrains Mono',Consolas,monospace; font-size:20px; font-weight:400; color:#1A4B7A;">
                    {source_id} · {chunk_id}{cited_badge}
                </span>
                <span style="font-size:20px; font-weight:700; color:{score_color}; text-transform:uppercase; letter-spacing:0.5px;">
                    Relevance: {score:.2f}
                </span>
            </div>
            <div class="evidence-snippet" style="border-left:3px solid #1A4B7A; padding:10px 16px; background:rgba(26,75,122,0.06); border-radius:0 6px 6px 0; margin:6px 0; font-size:20px; line-height:1.6; color:#1A1F26; white-space:pre-wrap; word-wrap:break-word; min-height:2em;">
                {preview_escaped}
            </div>
            <div style="font-size:20px; color:#525D6A; margin-top:10px; font-weight:500;">
                {authors} ({year}) · {venue} · {source_type}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Expandable section to see full excerpt (like Retrieval Filters)
    full_excerpt = full_text[:snippet_len] + ("..." if len(full_text) > snippet_len else "")
    with st.expander("Show full excerpt", expanded=False):
        st.markdown(
            f'<div style="font-size:20px; line-height:1.6; color:#1A1F26; white-space:pre-wrap;">{html.escape(full_excerpt)}</div>',
            unsafe_allow_html=True,
        )
    if len(full_text) > snippet_len:
        with st.expander("Show full chunk", expanded=False):
            st.markdown(
                f'<div style="font-size:20px; line-height:1.6; color:#1A1F26; white-space:pre-wrap;">{html.escape(full_text)}</div>',
                unsafe_allow_html=True,
            )


def render_status_strip(tone: str, pill_text: str, detail_text: str) -> None:
    """Render status strip in success/warning/info tone."""
    tone_map = {
        "success": "exec-status-tone-success",
        "warning": "exec-status-tone-warning",
        "info": "exec-status-tone-info",
        "error": "exec-status-tone-warning",
    }
    tone_class = tone_map.get((tone or "").lower(), "exec-status-tone-info")
    st.markdown(
        f"""
        <div class="exec-status-strip {tone_class}">
            <span class="exec-status-pill">{html.escape(pill_text)}</span>
            <span class="exec-status-text">{html.escape(detail_text)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_retrieval_disclosure(mode: str, detail: str) -> None:
    """Render retrieval disclosure bar."""
    mode_key = (mode or "standard").strip().lower()
    pill_class = "retrieval-pill-standard" if mode_key == "standard" else "retrieval-pill-fallback"
    mode_label = f"{mode_key.upper()} RETRIEVAL"
    st.markdown(
        f"""
        <div class="retrieval-disclosure">
            <div class="retrieval-disclosure-main">
                <span class="retrieval-pill {pill_class}">{html.escape(mode_label)}</span>
                <span class="retrieval-mode-title">{html.escape(detail)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _metric_color_class(value: float) -> str:
    """Return color class for metric value: green > 0.7, amber 0.5-0.7, red < 0.5."""
    v = float(value)
    if v > 0.7:
        return "metric-value-green"
    if v >= 0.5:
        return "metric-value-amber"
    return "metric-value-red"


def render_metric_card(value: str | float, label: str, color_tone: str | None = None) -> None:
    """Render a metric card with color coding: green > 0.7, amber 0.5-0.7, red < 0.5."""
    if color_tone is None and isinstance(value, (int, float)):
        v = float(value)
        if v > 0.7:
            color_tone = "green"
        elif v >= 0.5:
            color_tone = "amber"
        else:
            color_tone = "red"
    tone = (color_tone or "").lower()
    color_class = f"metric-value-{tone}" if tone in ("green", "amber", "red") else ""
    val_str = f"{value:.2f}" if isinstance(value, float) else str(value)
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value {color_class}">{html.escape(val_str)}</div>
            <div class="metric-label">{html.escape(label)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_eval_results_table(rows: list[dict]) -> None:
    """Render Per-Query Results table with color-coded metric columns (green > 0.7, amber 0.5-0.7, red < 0.5)."""
    if not rows:
        return
    headers = ["Query", "Type", "Groundedness", "Citation", "Relevance"]
    table_rows = []
    for r in rows:
        g = r.get("Groundedness", 0)
        c = r.get("Citation", 0)
        rel = r.get("Relevance", 0)
        g_class = _metric_color_class(g)
        c_class = _metric_color_class(c)
        rel_class = _metric_color_class(rel)
        g_str = f"{g:.2f}" if isinstance(g, (int, float)) else str(g)
        c_str = f"{c:.2f}" if isinstance(c, (int, float)) else str(c)
        rel_str = f"{rel:.2f}" if isinstance(rel, (int, float)) else str(rel)
        table_rows.append([
            html.escape(str(r.get("Query", ""))),
            html.escape(str(r.get("Type", ""))),
            f'<span class="{g_class}">{html.escape(g_str)}</span>',
            f'<span class="{c_class}">{html.escape(c_str)}</span>',
            f'<span class="{rel_class}">{html.escape(rel_str)}</span>',
        ])
    html_out = build_report_table(
        headers=headers,
        rows=table_rows,
        col_types=["long", "short", "short", "short", "short"],
        raw_html_cells=True,
        theme="evidence",
    )
    # st.html renders in isolated context; embed styles for metric colors and table layout
    wrapped = f'''<div class="eval-results-table" style="width:100%; overflow-x:auto; margin:0.5rem 0;">
<style>.metric-value-green{{color:#0D9668!important}}.metric-value-amber{{color:#D49717!important}}.metric-value-red{{color:#CC3333!important}}</style>
{html_out}</div>'''
    st.html(wrapped)


def render_empty_state(message: str, suggestion: str = "") -> None:
    """Render centered empty state."""
    suggestion_html = (
        f"<div style='font-style: italic; margin-top: 0.4rem;'>{html.escape(suggestion)}</div>"
        if suggestion
        else ""
    )
    st.markdown(
        f"""
        <div style="text-align:center; color:#525D6A; padding:2rem 1rem;">
            <div>{html.escape(message)}</div>
            {suggestion_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_card(source_dict: dict, key_prefix: str = "source") -> None:
    """Render one source card with View Chunks and Open Source actions."""
    source_id = str(source_dict.get("source_id", "Unknown"))
    title = str(source_dict.get("title", "Untitled"))
    authors = str(source_dict.get("authors", "Unknown authors"))
    year = str(source_dict.get("year", "Unknown year"))
    venue = str(source_dict.get("venue", "Unknown venue"))
    source_type = str(source_dict.get("source_type", "Unknown type"))
    relevance_note = str(source_dict.get("relevance_note", ""))
    chunk_count = int(source_dict.get("chunk_count", 0))
    url = str(source_dict.get("url_or_doi", "")).strip()
    chunk_previews = source_dict.get("chunk_previews", []) or []

    st.markdown(
        f"""
        <div class="thread-card source-card">
            <div class="source-card-authors">{html.escape(authors)} ({html.escape(year)})</div>
            <div class="source-card-title">"{html.escape(title)}"</div>
            <div class="source-card-meta">{html.escape(venue)} · {html.escape(source_type)} · ID: {html.escape(source_id)}</div>
            <div class="source-card-relevance">{html.escape(relevance_note)}</div>
            <div class="source-card-chunks">Chunks: {chunk_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    view_key = f"{key_prefix}_view_{source_id}"
    col1, col2 = st.columns(2)
    with col1:
        open_chunks = st.button("View Chunks", key=view_key, use_container_width=True)
    with col2:
        if url:
            st.markdown(
                f'''<a href="{html.escape(url)}" target="_blank" style="
                    display: block;
                    text-align: center;
                    padding: 0.8rem 1.5rem;
                    border: 1px solid #DDE1E7;
                    border-radius: 10px;
                    background: #FFFFFF;
                    color: #1A1F26;
                    font-size: 20px;
                    font-weight: 600;
                    text-decoration: none;
                    cursor: pointer;
                    box-sizing: border-box;
                    width: 100%;
                ">Open Source</a>''',
                unsafe_allow_html=True,
            )
        else:
            st.button("Open Source", key=f"{key_prefix}_open_disabled_{source_id}", disabled=True, use_container_width=True)

    if open_chunks:
        with st.expander(f"Chunks for {source_id}", expanded=True):
            if not chunk_previews:
                st.caption("No chunk previews available.")
            for idx, snippet in enumerate(chunk_previews, start=1):
                st.markdown(f"**{idx}.** {html.escape(snippet)}")


def render_thread_card(thread_dict: dict, key_prefix: str = "thread") -> dict:
    """Render one thread card and return action click states."""
    thread_id = str(thread_dict.get("id", "unknown"))
    query_text = str(thread_dict.get("query_preview", "Untitled query"))
    timestamp_text = str(thread_dict.get("timestamp_display", "Unknown time"))
    cited_count = int(thread_dict.get("sources_cited_count", 0))
    confidence = str(thread_dict.get("confidence_level", "Medium"))

    st.markdown(
        f"""
        <div class="thread-card">
            <div class="thread-title">{html.escape(query_text)}</div>
            <div class="thread-meta">
                {html.escape(timestamp_text)} · {cited_count} source{"s" if cited_count != 1 else ""} cited · Citation strength (count): {html.escape(confidence)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        view_clicked = st.button("View Thread", key=f"{key_prefix}_view_{thread_id}", width="stretch")
    with c2:
        resume_clicked = st.button("Resume Query", key=f"{key_prefix}_resume_{thread_id}", width="stretch")
    with c3:
        delete_clicked = st.button("Delete", key=f"{key_prefix}_delete_{thread_id}", width="stretch")

    return {
        "view": view_clicked,
        "resume": resume_clicked,
        "delete": delete_clicked,
    }


def render_failure_card(
    query: str,
    tag: str,
    what_wrong: str,
    retrieved_preview: str,
    answer_preview: str,
    suggested_fix: str,
) -> None:
    """Render an evaluation failure card with red left border and exec-status-pill tag."""
    q_display = html.escape(query[:120] + ("..." if len(query) > 120 else ""))
    tag_esc = html.escape(tag)
    what_esc = html.escape(what_wrong)
    ret_esc = html.escape(retrieved_preview[:400])
    ans_esc = html.escape(answer_preview[:400])
    fix_esc = html.escape(suggested_fix)
    st.markdown(
        f"""
        <div class="thread-card failure-card" style="border-left: 4px solid #CC3333; margin-bottom: 16px;">
            <div class="failure-card-line"><strong>Query:</strong> "{q_display}"</div>
            <div style="margin-bottom: 10px;">
                <span class="exec-status-pill" style="color:#CC3333; background:rgba(204,51,51,0.12); border:1px solid rgba(204,51,51,0.3);">{tag_esc}</span>
            </div>
            <div class="failure-card-line"><strong>What went wrong:</strong> {what_esc}</div>
            <div class="failure-card-line"><strong>Retrieved evidence:</strong> {ret_esc}</div>
            <div class="failure-card-line"><strong>Generated answer:</strong> {ans_esc}</div>
            <div class="failure-card-line"><strong>Suggested fix:</strong> {fix_esc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

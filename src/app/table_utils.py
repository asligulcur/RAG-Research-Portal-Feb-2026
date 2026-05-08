"""
Report table utilities — explicit column widths, no Pandoc.
Use build_report_table() for HTML and table_to_pdf() for PDF.
"""

import html
from typing import List, Optional

# Optional FPDF for PDF export
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False


def build_report_table(
    headers: List[str],
    rows: List[List[str]],
    col_types: Optional[List[str]] = None,
    *,
    raw_html_cells: bool = False,
    theme: str = "default",  # "default" | "report" | "evidence" — evidence uses larger fonts for st.html
) -> str:
    """
    Build an HTML table with sensible column widths.

    col_types: list matching headers length. Each entry is one of:
        "id"       → narrow (8%)   - source IDs, chunk IDs, short codes
        "short"    → small (12%)   - confidence, year, type, score
        "medium"   → moderate (20%) - claims, titles, names
        "long"     → wide (30%)    - evidence snippets, notes, descriptions
        "auto"     → no fixed width, takes remaining space

    If col_types is None, widths are auto-assigned based on average content length.
    """
    width_map = {"id": "8%", "short": "12%", "medium": "20%", "long": "30%", "auto": ""}

    if col_types is None:
        col_types = []
        for i, header in enumerate(headers):
            avg_len = sum(len(str(row[i])) for row in rows if i < len(row)) / max(len(rows), 1)
            if avg_len < 15:
                col_types.append("short")
            elif avg_len < 50:
                col_types.append("medium")
            else:
                col_types.append("long")

    # Build colgroup
    colgroup = "<colgroup>"
    for ct in col_types:
        w = width_map.get(ct, "")
        if w:
            colgroup += f'<col style="width:{w}">'
        else:
            colgroup += "<col>"
    colgroup += "</colgroup>"

    use_report_theme = theme == "report"
    use_evidence_theme = theme == "evidence"
    th_font = "17px" if use_evidence_theme else "13px"
    td_font = "20px" if use_evidence_theme else "14px"

    # Build header
    thead = "<thead><tr>"
    for h in headers:
        if use_report_theme:
            thead += f"<th>{html.escape(str(h))}</th>"
        else:
            thead += f'''<th style="
            padding:10px 14px;
            font-size:{th_font} !important;
            font-weight:700;
            text-transform:uppercase;
            letter-spacing:0.5px;
            color:#0F2B46;
            background:#F4F5F7;
            border-bottom:2px solid #DDE1E7;
            text-align:left;
            vertical-align:bottom;
        ">{html.escape(str(h))}</th>'''
    thead += "</tr></thead>"

    # Build rows
    tbody = "<tbody>"
    for row in rows:
        tbody += "<tr>"
        for i, cell in enumerate(row):
            ct = col_types[i] if i < len(col_types) else "auto"
            wrap = "word-wrap:break-word; overflow-wrap:break-word;" if ct in ("medium", "long") or use_evidence_theme else ""
            max_w = "max-width:300px;" if ct == "long" else "max-width:200px;" if ct == "medium" else ""
            cell_esc = str(cell) if raw_html_cells else html.escape(str(cell))
            if use_report_theme:
                tbody += f'<td style="{wrap} {max_w}">{cell_esc}</td>'
            else:
                tbody += f'''<td style="
                padding:12px 14px;
                font-size:{td_font} !important;
                line-height:1.5;
                color:#1A1F26;
                border-bottom:1px solid #DDE1E7;
                vertical-align:top;
                {wrap}
                {max_w}
            ">{cell_esc}</td>'''
        tbody += "</tr>"
    tbody += "</tbody>"

    table_style = "width:100%; border-collapse:collapse; table-layout:fixed;"
    wrapper_font = td_font if use_evidence_theme else "14px"
    wrapper = ' class="table-wrapper"' if use_report_theme else f' style="font-size:{wrapper_font} !important; overflow-x:auto;"'
    return f'''<div{wrapper}>
        <table style="{table_style}">
            {colgroup}
            {thead}
            {tbody}
        </table>
    </div>'''


def add_image_to_pdf(pdf: "FPDF", image_path: str) -> None:
    """Insert image at full content width. Use for report PDFs with figures."""
    if not HAS_FPDF:
        raise ImportError("fpdf2 is required for PDF export. pip install fpdf2")
    content_width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.image(image_path, x=pdf.l_margin, w=content_width)
    pdf.ln(10)


def table_to_pdf(
    pdf: "FPDF",
    headers: List[str],
    rows: List[List[str]],
    col_types: List[str],
) -> None:
    """
    Render a table to fpdf2 FPDF with proportional column widths.
    """
    if not HAS_FPDF:
        raise ImportError("fpdf2 is required for PDF export. pip install fpdf2")

    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    width_pct = {"id": 0.08, "short": 0.12, "medium": 0.20, "long": 0.30, "auto": 0.15}
    col_widths = [width_pct.get(ct, 0.15) * page_width for ct in col_types]

    # Normalize so widths sum to page_width
    total = sum(col_widths)
    if total > 0:
        col_widths = [w * page_width / total for w in col_widths]

    # Header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(244, 245, 247)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, str(h)[:80], border=1, fill=True)
    pdf.ln()

    # Rows
    pdf.set_font("Helvetica", "", 8)
    for row in rows:
        max_lines = 1
        for i, cell in enumerate(row):
            if i < len(col_widths):
                lines = pdf.multi_cell(col_widths[i], 5, str(cell)[:150], split_only=True)
                max_lines = max(max_lines, len(lines))
        row_h = max_lines * 5
        y_start = pdf.get_y()
        x = pdf.l_margin
        for i, cell in enumerate(row):
            if i < len(col_widths):
                pdf.set_xy(x, y_start)
                pdf.multi_cell(col_widths[i], 5, str(cell)[:150], border=1)
                x += col_widths[i]
        pdf.set_xy(pdf.l_margin, y_start + row_h)

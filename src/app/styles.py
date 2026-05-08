"""
Professional styling for AG Research Portal
Executive-grade design system

Root cause found: Streamlit 1.54 uses [data-testid="stMainBlockContainer"]
not .main. All CSS must target the correct selector.

Single-layer approach:
  - AG_RESEARCH_CSS is injected via st.markdown with selectors specific
    to Streamlit 1.54 containers and widgets.
"""

# Alias for the main content container in Streamlit 1.54
_M = '[data-testid="stMainBlockContainer"]'
_S = '[data-testid="stSidebar"]'

AG_RESEARCH_CSS = f"""
<style>
    :root {{
        --navy:        #0F2B46;
        --royal:       #1A4B7A;
        --gold:        #C5A028;
        --gold-light:  #E8D48B;
        --charcoal:    #1A1F26;
        --slate:       #525D6A;
        --border:      #DDE1E7;
        --green:       #0D9668;
        --amber:       #D49717;
        --success-green:#0D9668;
        --error-red:   #CC3333;
        --white:       #FFFFFF;
    }}

    /* ── Base ─────────────────────────────────────────────── */
    html, body, [data-testid="stAppViewContainer"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                     Roboto, 'Helvetica Neue', Arial, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
        background: #F4F5F7 !important;
    }}

    {_M} {{
        padding: 2.5rem 3.5rem 3rem 3.5rem !important;
        max-width: 1250px !important;
    }}

    /* ── Sidebar ──────────────────────────────────────────── */
    {_S},
    {_S} > div:first-child,
    section{_S},
    section{_S} > div:first-child {{
        background: linear-gradient(180deg, #0F2B46 0%, #0A1F35 100%) !important;
        border-right: none !important;
    }}

    {_S} hr {{
        border-color: rgba(255,255,255,0.1) !important;
    }}

    /* ── Sidebar buttons ─────────────────────────────────── */
    {_S} button,
    section{_S} button,
    {_S} [data-testid="stBaseButton-secondary"] button,
    {_S} .stButton > button {{
        background: transparent !important;
        border: none !important;
        border-left: 3px solid transparent !important;
        border-radius: 0 8px 8px 0 !important;
        color: rgba(255,255,255,0.55) !important;
        font-size: 20px !important;
        font-weight: 600 !important;
        padding: 0.9rem 1.4rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
        display: flex !important;
        box-shadow: none !important;
        width: 100% !important;
    }}
    {_S} button:hover,
    section{_S} button:hover {{
        background: rgba(255,255,255,0.07) !important;
        color: rgba(255,255,255,0.9) !important;
        box-shadow: none !important;
    }}
    {_S} button p,
    section{_S} button p {{
        font-size: 20px !important;
        color: rgba(255,255,255,0.86) !important;
        font-weight: 600 !important;
    }}
    {_S} button:hover p,
    section{_S} button:hover p {{
        color: #FFFFFF !important;
    }}

    /* ── Headings ─────────────────────────────────────────── */
    {_M} h1 {{ font-size: 44px !important; font-weight: 800 !important; color: #0F2B46 !important; letter-spacing: -0.5px !important; }}
    {_M} h2 {{ font-size: 32px !important; font-weight: 700 !important; color: #0F2B46 !important; }}
    {_M} h3 {{ font-size: 26px !important; font-weight: 700 !important; color: #0F2B46 !important; }}
    {_M} h4 {{ font-size: 22px !important; font-weight: 600 !important; color: #1A1F26 !important; }}

    {_M} p,
    {_M} .stMarkdown p,
    {_M} [data-testid="stMarkdownContainer"] p,
    {_M} .stText,
    {_M} [data-testid="stText"] {{
        font-size: 20px !important;
        line-height: 1.7 !important;
        color: #1A1F26 !important;
    }}

    /* Evidence table: override global p rule; no p tags inside cells */
    {_M} .evidence-table-wrapper,
    {_M} .evidence-table-wrapper table,
    {_M} .evidence-table-wrapper td,
    {_M} .evidence-table-wrapper td * {{
        font-size: 20px !important;
    }}
    {_M} .evidence-table-wrapper th,
    {_M} .evidence-table-wrapper th * {{
        font-size: 17px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        color: #0F2B46 !important;
    }}
    {_M} .evidence-table-wrapper td,
    {_M} .evidence-table-wrapper td * {{
        color: #1A1F26 !important;
    }}
    /* Citation column: match table body (override .citation chip styling) */
    {_M} .evidence-table-wrapper .citation {{
        font-size: 20px !important;
        font-weight: 400 !important;
        font-family: inherit !important;
        background: none !important;
        padding: 0 !important;
    }}

    /* ── Buttons ──────────────────────────────────────────── */
    {_M} button {{
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 20px !important;
        padding: 0.8rem 1.5rem !important;
    }}

    /* Primary button - navy bg, white text (app-wide, high specificity to override Streamlit theme) */
    html body [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"] > button,
    html body [data-testid="stAppViewContainer"] [data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primary"] > button,
    html body [data-testid="stAppViewContainer"] [data-testid="stFormSubmitButton"] button,
    {_M} [data-testid="stBaseButton-primary"] > button {{
        background: #0F2B46 !important;
        border: 1px solid #0F2B46 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(15, 43, 70, 0.25) !important;
        font-weight: 700 !important;
    }}
    html body [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"] > button:hover,
    html body [data-testid="stAppViewContainer"] [data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primary"] > button:hover,
    html body [data-testid="stAppViewContainer"] [data-testid="stFormSubmitButton"] button:hover,
    {_M} [data-testid="stBaseButton-primary"] > button:hover {{
        background: #1A4B7A !important;
        border-color: #1A4B7A !important;
    }}
    html body [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"] > button,
    html body [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"] > button p,
    html body [data-testid="stAppViewContainer"] [data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primary"] > button *,
    html body [data-testid="stAppViewContainer"] [data-testid="stFormSubmitButton"] button *,
    {_M} [data-testid="stBaseButton-primary"] > button,
    {_M} [data-testid="stBaseButton-primary"] > button p,
    {_M} [data-testid="stBaseButton-primary"] > button * {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        opacity: 1 !important;
    }}

    /* Wildcard catches every nested child (p, span, etc.) that Streamlit wraps text in */
    html body [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"] button *,
    html body [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"] button p,
    html body [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"] button span,
    {_M} [data-testid="stBaseButton-primary"] button *,
    {_S} [data-testid="stBaseButton-primary"] button * {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        opacity: 1 !important;
    }}

    {_M} button[kind="secondary"],
    {_M} [data-testid="stBaseButton-secondary"] > button,
    {_M} button[data-testid="baseButton-secondary"] {{
        background: #FFFFFF !important;
        border: 1px solid #DDE1E7 !important;
        color: #1A1F26 !important;
    }}

    /* Dashboard thread row buttons */
    {_M} button[kind="secondary"] p,
    {_M} [data-testid="stBaseButton-secondary"] > button p {{
        text-align: left !important;
        width: 100% !important;
        margin: 0 !important;
    }}

    /* ── Inputs ───────────────────────────────────────────── */
    {_M} [data-testid="stTextInput"] input,
    {_M} [data-baseweb="input"] input,
    {_M} input[type="text"],
    {_M} input[aria-label] {{
        font-size: 22px !important;
        padding: 1rem 1.4rem !important;
        border-radius: 10px !important;
        border: 2px solid #DDE1E7 !important;
        min-height: 56px !important;
        box-sizing: border-box !important;
        height: auto !important;
    }}

    {_M} [data-testid="stTextArea"] textarea {{
        font-size: 22px !important;
        line-height: 1.45 !important;
        min-height: 122px !important;
        padding: 1rem 1.15rem !important;
        border-radius: 10px !important;
        border: 2px solid #DDE1E7 !important;
    }}

    {_M} [data-testid="stTextArea"] textarea::placeholder {{
        font-size: 20px !important;
        color: #9CA3AF !important;
    }}
    {_M} [data-testid="stTextInput"] > div,
    {_M} [data-testid="stTextInput"] > div > div {{
        min-height: 56px !important;
    }}
    {_M} input::placeholder {{
        font-size: 20px !important;
        color: #9CA3AF !important;
    }}
    {_M} input:focus {{
        border-color: #1A4B7A !important;
        box-shadow: 0 0 0 4px rgba(26, 75, 122, 0.12) !important;
    }}

    /* ── Labels ───────────────────────────────────────────── */
    {_M} label {{
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #1A1F26 !important;
    }}

    /* ── Expanders ────────────────────────────────────────── */
    {_M} summary {{
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #0F2B46 !important;
    }}

    /* ── Alerts ───────────────────────────────────────────── */
    {_M} [data-testid="stAlert"] {{
        font-size: 20px !important;
        padding: 1.1rem 1.35rem !important;
        border-radius: 8px !important;
    }}

    /* ── Executive Summary ────────────────────────────────── */
    .executive-summary {{
        background: #FFFFFF;
        border-left: 5px solid #C5A028;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin: 1.25rem 0;
        font-size: 20px !important;
        line-height: 1.6 !important;
    }}
    /* Override global p (22px) so synthesis memo and answer body stay at 20px */
    {_M} .executive-summary,
    {_M} .executive-summary p,
    {_M} .executive-summary li,
    {_M} .executive-summary div,
    {_M} .executive-summary span:not(.citation),
    [data-testid="stAppViewContainer"] .executive-summary,
    [data-testid="stAppViewContainer"] .executive-summary p,
    [data-testid="stAppViewContainer"] .executive-summary li,
    [data-testid="stAppViewContainer"] .executive-summary div,
    [data-testid="stAppViewContainer"] .executive-summary span:not(.citation) {{
        font-size: 20px !important;
        line-height: 1.6 !important;
    }}
    .retrieval-disclosure {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        background: #FFFFFF;
        border: 1px solid #DDE1E7;
        border-radius: 10px;
        padding: 0.85rem 1rem;
        margin: 0.65rem 0 1rem 0;
        box-shadow: 0 1px 5px rgba(10, 31, 53, 0.04);
    }}

    .retrieval-disclosure-main {{
        display: flex;
        align-items: center;
        gap: 0.7rem;
        flex-wrap: wrap;
    }}

    .retrieval-pill {{
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 0.28rem 0.75rem;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        border: 1px solid transparent;
        line-height: 1.1;
    }}

    .retrieval-pill-standard {{
        color: #0D9668;
        background: rgba(13, 150, 104, 0.08);
        border-color: rgba(13, 150, 104, 0.22);
    }}

    .retrieval-pill-fallback {{
        color: #A25B00;
        background: rgba(212, 151, 23, 0.12);
        border-color: rgba(212, 151, 23, 0.26);
    }}

    .retrieval-mode-title {{
        color: #0F2B46;
        font-size: 16px;
        font-weight: 700;
    }}

    .retrieval-mode-subtext {{
        color: #525D6A;
        font-size: 14px;
        font-weight: 500;
    }}

    .exec-status-strip {{
        display: flex;
        align-items: center;
        gap: 0.7rem;
        background: #FFFFFF;
        border: 1px solid #DDE1E7;
        border-left: 4px solid #CBD5E1;
        border-radius: 10px;
        padding: 0.72rem 0.9rem;
        margin: 0.55rem 0;
    }}

    .exec-status-pill {{
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 0.22rem 0.65rem;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        line-height: 1.1;
        border: 1px solid transparent;
        white-space: nowrap;
    }}

    .exec-status-text {{
        color: #1A1F26;
        font-size: 14px;
        font-weight: 600;
    }}

    .exec-status-tone-success {{
        border-left-color: #0D9668;
        background: linear-gradient(90deg, rgba(13,150,104,0.04), #FFFFFF 38%);
    }}
    .exec-status-tone-success .exec-status-pill {{
        color: #0D9668;
        background: rgba(13,150,104,0.1);
        border-color: rgba(13,150,104,0.24);
    }}

    .exec-status-tone-info {{
        border-left-color: #1A4B7A;
        background: linear-gradient(90deg, rgba(26,75,122,0.05), #FFFFFF 38%);
    }}
    .exec-status-tone-info .exec-status-pill {{
        color: #1A4B7A;
        background: rgba(26,75,122,0.12);
        border-color: rgba(26,75,122,0.26);
    }}

    .exec-status-tone-warning {{
        border-left-color: #D49717;
        background: linear-gradient(90deg, rgba(212,151,23,0.06), #FFFFFF 38%);
    }}
    .exec-status-tone-warning .exec-status-pill {{
        color: #A25B00;
        background: rgba(212,151,23,0.14);
        border-color: rgba(212,151,23,0.28);
    }}

    .citation {{
        background: #EEF2F7;
        padding: 0.3rem 0.6rem;
        border-radius: 4px;
        font-family: 'SF Mono', 'JetBrains Mono', Consolas, monospace;
        font-size: 17px !important;
        color: #1A4B7A;
        font-weight: 400;
    }}

    .dashboard-widget {{
        background: #FFFFFF;
        border: 1px solid #DDE1E7;
        border-radius: 10px;
        padding: 1.75rem;
        box-shadow: 0 1px 6px rgba(0,0,0,0.03);
    }}

    .widget-title {{
        color: #0F2B46;
        font-size: 22px !important;
        font-weight: 700 !important;
        margin-bottom: 1rem;
        border-bottom: 2px solid #C5A028;
        padding-bottom: 0.6rem;
    }}

    .thread-card {{
        background: #FFFFFF;
        border: 1px solid #DDE1E7;
        border-radius: 10px;
        padding: 1.2rem 1.25rem;
        box-shadow: 0 1px 4px rgba(10, 31, 53, 0.04);
    }}

    /* Evidence snippet: match evaluation dashboard text size (20px) */
    .thread-card .evidence-snippet,
    .thread-card .evidence-snippet * {{
        font-size: 20px !important;
        font-weight: 400 !important;
    }}

    {_M} .failure-card,
    {_M} .failure-card *,
    {_M} .failure-card .failure-card-line,
    {_M} .failure-card .failure-card-line *,
    {_M} .failure-card h1, {_M} .failure-card h2, {_M} .failure-card h3, {_M} .failure-card h4,
    {_M} .failure-card p {{
        font-size: 20px !important;
        line-height: 1.5 !important;
        font-family: inherit !important;
        font-weight: 400 !important;
    }}
    {_M} .failure-card strong,
    {_M} .failure-card .failure-card-line strong {{
        font-weight: 700 !important;
    }}
    .failure-card .failure-card-line {{
        margin-bottom: 8px;
    }}
    .failure-card .failure-card-line:last-child {{
        margin-bottom: 0;
    }}

    .thread-title {{
        color: #0F2B46;
        font-weight: 700;
        font-size: 21px;
        margin-bottom: 0.35rem;
    }}

    .thread-meta {{
        color: #525D6A;
        font-size: 17px !important;
        font-weight: 500;
    }}
    .thread-card .thread-meta,
    .thread-card .thread-meta * {{
        font-size: 17px !important;
    }}

    /* Source card: 20px for readable content; 17px only for citation/ID line */
    {_M} .source-card .source-card-authors {{
        font-size: 21px !important;
        color: #0F2B46 !important;
        font-weight: 700 !important;
        margin-bottom: 0.35rem !important;
    }}
    {_M} .source-card .source-card-title {{
        font-size: 21px !important;
        font-weight: 600 !important;
        color: #1A1F26 !important;
        margin-bottom: 0.4rem !important;
    }}
    {_M} .source-card .source-card-meta {{
        font-size: 20px !important;
        color: #525D6A !important;
        font-weight: 500 !important;
    }}
    {_M} .source-card .source-card-relevance {{
        font-size: 20px !important;
        color: #0F2B46 !important;
        font-style: italic !important;
        margin-top: 0.6rem !important;
    }}
    {_M} .source-card .source-card-chunks {{
        font-size: 20px !important;
        color: #525D6A !important;
        font-weight: 600 !important;
        margin-top: 0.6rem !important;
    }}

    /* Source card: View Chunks and Open Source buttons same width */
    {_M} div:has(.source-card) + div [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }}
    {_M} div:has(.source-card) + div [data-testid="stHorizontalBlock"] button,
    {_M} div:has(.source-card) + div [data-testid="stHorizontalBlock"] a[role="button"] {{
        width: 100% !important;
        min-width: 100% !important;
        box-sizing: border-box !important;
    }}

    .metric-card {{
        background: #FFFFFF;
        border: 1px solid #DDE1E7;
        border-radius: 10px;
        padding: 1rem 1.1rem;
        box-shadow: 0 1px 4px rgba(10, 31, 53, 0.04);
        font-family: inherit !important;
    }}

    .metric-value {{
        color: #0F2B46;
        font-size: 34px;
        line-height: 1.1;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }}

    .metric-value-green {{ color: #0D9668 !important; }}
    .metric-value-amber {{ color: #D49717 !important; }}
    .metric-value-red {{ color: #CC3333 !important; }}

    .eval-results-table {{
        width: 100%;
        overflow-x: auto;
        margin: 0.5rem 0;
    }}
    .eval-results-table table {{
        width: 100%;
        table-layout: auto;
        border-collapse: collapse;
        font-size: 20px;
        line-height: 1.5;
        font-family: inherit;
    }}
    .eval-results-table th, .eval-results-table td {{
        padding: 0.65rem 0.9rem;
        text-align: left;
        border-bottom: 1px solid #DDE1E7;
        white-space: normal;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }}
    .eval-results-table td:first-child,
    .eval-results-table th:first-child {{
        width: 45%;
        min-width: 180px;
    }}
    .eval-results-table th:nth-child(3),
    .eval-results-table td:nth-child(3) {{
        min-width: 140px;
    }}
    .eval-results-table th {{
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #0F2B46;
        font-size: 17px;
        white-space: nowrap;
    }}
    .eval-results-table td {{
        color: #1A1F26;
        font-size: 20px;
    }}

    .metric-label {{
        color: #525D6A;
        font-size: 15px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* ── Chrome ───────────────────────────────────────────── */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header {{ visibility: hidden; }}

    ::-webkit-scrollbar {{ width: 8px; }}
    ::-webkit-scrollbar-track {{ background: #F0F1F3; }}
    ::-webkit-scrollbar-thumb {{ background: #B0B7C3; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #525D6A; }}
</style>
"""

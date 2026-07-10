"""
Citation validation and normalization — pure string logic, no Streamlit/model deps.

Extracted from app.py so the trust-critical validator can be unit-tested in
isolation (see tests/test_citation_validator.py). This is the code-level defense
that strips fabricated citations the model may emit.
"""

import re


def normalize_bare_citations(text: str) -> str:
    """Convert bare 'SourceID, ChunkID' or 'SourceID ChunkID' to [Source: X, Chunk: Y] so render_citations can style them."""
    def _wrap(m: re.Match) -> str:
        return f"[Source: {m.group(1)}, Chunk: {m.group(2)}]"
    text = re.sub(r"(\w+_\d{4}),\s*(\1_chunk_\d+)", _wrap, text)
    text = re.sub(r"(\w+_\d{4})\s+(\1_chunk_\d+)", _wrap, text)
    return text


def validate_citations_in_answer(answer: str, valid_source_ids: set[str]) -> tuple[str, bool]:
    """Strip fabricated citations (source_id not in corpus) from answer. Return (cleaned_answer, had_fabricated)."""
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
    # [Source: X] — bare/malformed source tag with no Chunk part (e.g. "[Source: All excerpts]").
    # Catches vague, chunk-less attributions the model invents; a valid bare source id is kept.
    pattern1c = re.compile(r"\[Source:\s*([^,\]]+)\]")
    text = pattern1c.sub(_replace_invalid, text)
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

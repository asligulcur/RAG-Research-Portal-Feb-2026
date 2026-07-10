"""
Unit tests for the citation validator — the trust-critical defense that strips
fabricated citations the model may emit. Run: `pytest tests/test_citation_validator.py`

No API key, model, or Streamlit needed: the validator is pure string logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "app"))

from citation_validator import validate_citations_in_answer, normalize_bare_citations  # noqa: E402

VALID = {"RealPaper_2024", "SmallLM_2023"}


def test_valid_well_formed_citation_is_kept():
    ans = "SLMs are efficient [Source: RealPaper_2024, Chunk: RealPaper_2024_chunk_3]."
    cleaned, fabricated = validate_citations_in_answer(ans, VALID)
    assert not fabricated
    assert "RealPaper_2024" in cleaned


def test_well_formed_fabricated_citation_is_stripped_and_flagged():
    ans = "This is invented [Source: FakePaper_2099, Chunk: FakePaper_2099_chunk_1]."
    cleaned, fabricated = validate_citations_in_answer(ans, VALID)
    assert fabricated
    assert "FakePaper_2099" not in cleaned


def test_bare_all_excerpts_citation_is_stripped_and_flagged():
    """Regression: the malformed '[Source: All excerpts]' form the README advertises must be caught."""
    ans = "Model X outperforms model Y [Source: All excerpts]."
    cleaned, fabricated = validate_citations_in_answer(ans, VALID)
    assert fabricated, "'[Source: All excerpts]' should be flagged as fabricated"
    assert "All excerpts" not in cleaned, "'[Source: All excerpts]' should be stripped"


def test_valid_bare_source_tag_is_kept():
    """A chunk-less but real source id must NOT be stripped by the new bare-tag pattern."""
    ans = "See the survey [Source: SmallLM_2023]."
    cleaned, fabricated = validate_citations_in_answer(ans, VALID)
    assert not fabricated
    assert "SmallLM_2023" in cleaned


def test_normalize_wraps_bare_citation_form():
    text = "Efficiency matters RealPaper_2024, RealPaper_2024_chunk_2."
    assert "[Source: RealPaper_2024, Chunk: RealPaper_2024_chunk_2]" in normalize_bare_citations(text)

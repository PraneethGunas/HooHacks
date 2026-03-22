"""Tests for the upgraded CBO search (Tavily advanced + raw content)."""

import pytest
from backend.tools.search_cbo_reports import search_cbo_reports
from backend.tools.schemas import SearchCBOOutput


@pytest.mark.asyncio
async def test_cbo_returns_full_content():
    """Verify CBO search now returns full report text, not just snippets."""
    r = await search_cbo_reports("federal minimum wage employment effects", limit=1)
    assert isinstance(r, SearchCBOOutput)
    assert len(r.results) > 0
    report = r.results[0]
    # Should have substantially more content than old 400-char snippet
    assert len(report.snippet) > 1000, f"Expected >1000 chars, got {len(report.snippet)}"
    assert "minimum wage" in report.snippet.lower()
    print(f"\nCBO report: {report.title}")
    print(f"Content length: {len(report.snippet)} chars")


@pytest.mark.asyncio
async def test_cbo_basic_mode():
    """Verify basic (non-deep) mode still works."""
    r = await search_cbo_reports("tariff consumer prices", limit=2, deep=False)
    assert isinstance(r, SearchCBOOutput)
    assert len(r.results) > 0
    # Basic mode returns shorter snippets
    print(f"\nBasic mode: {len(r.results)} results")
    for rep in r.results:
        print(f"  {rep.title[:60]} ({len(rep.snippet)} chars)")

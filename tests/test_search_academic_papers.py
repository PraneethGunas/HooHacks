import pytest
from backend.tools.search_academic_papers import search_academic_papers
from backend.tools.schemas import SearchPapersOutput


@pytest.mark.asyncio
async def test_search_papers_basic():
    """Search for minimum wage employment elasticity papers."""
    result = await search_academic_papers(
        query="minimum wage employment elasticity", limit=3
    )
    assert isinstance(result, SearchPapersOutput)
    assert len(result.results) > 0
    print(f"\nFound {result.total_results} total papers, showing {len(result.results)}:")
    for p in result.results:
        print(f"  [{p.year}] {p.title} (cited: {p.citations})")
        if p.tldr:
            print(f"    TLDR: {p.tldr[:120]}")


@pytest.mark.asyncio
async def test_search_papers_recent():
    """Search for recent papers only (2022-2026)."""
    result = await search_academic_papers(
        query="minimum wage price pass-through", year_range="2022-2026", limit=3
    )
    assert isinstance(result, SearchPapersOutput)
    for p in result.results:
        if p.year:
            assert p.year >= 2022
    print(f"\nRecent papers: {[p.title[:60] for p in result.results]}")

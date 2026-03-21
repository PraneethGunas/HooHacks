import pytest
from backend.tools.search_openalex import search_openalex
from backend.tools.schemas import SearchOpenAlexOutput


@pytest.mark.asyncio
async def test_openalex_basic():
    """Search for minimum wage research — sorted by citations."""
    result = await search_openalex(
        query="minimum wage employment effects", limit=3
    )
    assert isinstance(result, SearchOpenAlexOutput)
    assert len(result.results) > 0
    print(f"\nOpenAlex results ({len(result.results)}):")
    for w in result.results:
        print(f"  [{w.year}] {w.title} (cited: {w.citations})")
        if w.abstract:
            print(f"    Abstract: {w.abstract[:100]}...")
        if w.open_access_url:
            print(f"    OA: {w.open_access_url}")


@pytest.mark.asyncio
async def test_openalex_sort_by_date():
    """Search sorted by publication date for newest research."""
    result = await search_openalex(
        query="minimum wage policy effects", sort_by="publication_date", limit=3
    )
    assert isinstance(result, SearchOpenAlexOutput)
    assert len(result.results) > 0
    print(f"\nNewest papers: {[(w.year, w.title[:50]) for w in result.results]}")

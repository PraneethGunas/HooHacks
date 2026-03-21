import pytest
from backend.tools.search_cbo_reports import search_cbo_reports
from backend.tools.schemas import SearchCBOOutput


@pytest.mark.asyncio
async def test_cbo_minimum_wage():
    """Search CBO for minimum wage analysis reports."""
    result = await search_cbo_reports(
        query="federal minimum wage employment effects", limit=3
    )
    assert isinstance(result, SearchCBOOutput)
    assert len(result.results) > 0
    print(f"\nCBO reports ({len(result.results)}):")
    for r in result.results:
        print(f"  {r.title}")
        print(f"    URL: {r.url}")
        print(f"    Score: {r.score}")
        print(f"    Snippet: {r.snippet[:120]}...")

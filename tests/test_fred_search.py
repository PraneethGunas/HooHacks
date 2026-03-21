import pytest
from backend.tools.fred_search import fred_search
from backend.tools.schemas import FredSearchOutput


@pytest.mark.asyncio
async def test_fred_search_basic():
    """Search for unemployment rate — should find UNRATE."""
    result = await fred_search(query="unemployment rate", limit=3)
    assert isinstance(result, FredSearchOutput)
    assert len(result.results) > 0
    assert len(result.results) <= 3
    for r in result.results:
        assert r.id
        assert r.title
    print(f"\nFound {len(result.results)} series:")
    for r in result.results:
        print(f"  {r.id}: {r.title} ({r.units}, {r.frequency})")


@pytest.mark.asyncio
async def test_fred_search_minimum_wage():
    """Search for federal minimum wage series."""
    result = await fred_search(query="federal minimum wage")
    assert isinstance(result, FredSearchOutput)
    assert len(result.results) > 0
    ids = [r.id for r in result.results]
    print(f"\nMinimum wage series: {ids}")

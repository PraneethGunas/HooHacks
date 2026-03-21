import pytest
from backend.tools.web_search_news import web_search_news
from backend.tools.schemas import WebSearchOutput


@pytest.mark.asyncio
async def test_web_search_recent():
    """Search for recent minimum wage news."""
    result = await web_search_news(
        query="federal minimum wage increase 2026", recency="past_year"
    )
    assert isinstance(result, WebSearchOutput)
    assert len(result.results) > 0
    print(f"\nNews results ({len(result.results)}):")
    for a in result.results:
        print(f"  {a.title}")
        print(f"    Date: {a.published_date}")
        print(f"    Content: {a.content[:100]}...")

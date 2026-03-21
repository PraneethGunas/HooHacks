from __future__ import annotations

from backend.config import settings
from backend.tools._tavily import _tavily_search
from backend.tools.schemas import NewsArticle, WebSearchOutput

RECENCY_MAP = {
    "past_week": 7,
    "past_month": 30,
    "past_year": 365,
}


async def web_search_news(
    query: str, recency: str = "past_month"
) -> WebSearchOutput:
    """Search the web for recent news and policy developments."""
    days = RECENCY_MAP.get(recency, 30)
    raw = await _tavily_search(
        query,
        api_key=settings.tavily_api_key,
        max_results=5,
        days=days,
    )
    results = [
        NewsArticle(
            title=r.get("title", ""),
            url=r.get("url", ""),
            content=(r.get("content", ""))[:300],
            published_date=r.get("published_date"),
        )
        for r in raw
    ]
    return WebSearchOutput(results=results, query=query)

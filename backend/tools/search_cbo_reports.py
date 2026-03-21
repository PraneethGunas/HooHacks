from __future__ import annotations

from backend.config import settings
from backend.tools._tavily import _tavily_search
from backend.tools.schemas import CBOReport, SearchCBOOutput


async def search_cbo_reports(query: str, limit: int = 5) -> SearchCBOOutput:
    """Search cbo.gov for Congressional Budget Office reports."""
    raw = await _tavily_search(
        query,
        api_key=settings.tavily_api_key,
        include_domains=["cbo.gov"],
        max_results=limit,
    )
    results = [
        CBOReport(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=(r.get("content", ""))[:400],
            score=r.get("score", 0.0),
        )
        for r in raw
    ]
    return SearchCBOOutput(results=results, query=query)

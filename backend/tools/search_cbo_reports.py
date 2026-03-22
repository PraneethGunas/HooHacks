from __future__ import annotations

from backend.config import settings
from backend.tools._tavily import _tavily_search
from backend.tools.schemas import CBOReport, SearchCBOOutput


async def search_cbo_reports(
    query: str, limit: int = 5, deep: bool = True
) -> SearchCBOOutput:
    """Search cbo.gov for Congressional Budget Office reports.

    Uses Tavily advanced search with raw content extraction to bypass
    CBO's Cloudflare protection. Returns full report text when available.
    """
    raw = await _tavily_search(
        query,
        api_key=settings.tavily_api_key,
        include_domains=["cbo.gov"],
        max_results=limit,
        search_depth="advanced" if deep else "basic",
        include_raw_content=deep,
    )
    results = []
    for r in raw:
        # Use raw_content (full report) if available, otherwise snippet
        content = r.get("raw_content", "") or r.get("content", "")
        # Truncate to 8000 chars — enough for key findings without bloating context
        snippet = content[:8000] if len(content) > 8000 else content
        results.append(
            CBOReport(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=snippet,
                score=r.get("score", 0.0),
            )
        )
    return SearchCBOOutput(results=results, query=query)

from __future__ import annotations

from backend.tools._http import fetch_json

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


async def _tavily_search(
    query: str,
    *,
    api_key: str,
    include_domains: list[str] | None = None,
    max_results: int = 5,
    days: int | None = None,
) -> list[dict]:
    """Shared Tavily search implementation.

    Used by search_cbo_reports (include_domains=["cbo.gov"]) and
    web_search_news (days= for recency filtering).
    """
    body: dict = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }
    if include_domains:
        body["include_domains"] = include_domains
    if days is not None:
        body["days"] = days

    data = await fetch_json(TAVILY_SEARCH_URL, method="POST", json_body=body)
    return data.get("results", [])

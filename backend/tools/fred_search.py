from __future__ import annotations

from backend.config import settings
from backend.tools._http import fetch_json
from backend.tools.schemas import FredSearchOutput, FredSeriesMatch

FRED_SEARCH_URL = "https://api.stlouisfed.org/fred/series/search"


async def fred_search(query: str, limit: int = 5) -> FredSearchOutput:
    """Search FRED for economic data series by keyword."""
    params = {
        "search_text": query,
        "api_key": settings.fred_api_key,
        "file_type": "json",
        "limit": limit,
        "order_by": "search_rank",
    }
    data = await fetch_json(FRED_SEARCH_URL, params=params)

    series_list = data.get("seriess", [])
    results = [
        FredSeriesMatch(
            id=s["id"],
            title=s.get("title", ""),
            units=s.get("units", ""),
            frequency=s.get("frequency", ""),
            seasonal_adjustment=s.get("seasonal_adjustment", ""),
            last_updated=s.get("last_updated", ""),
            popularity=s.get("popularity", 0),
        )
        for s in series_list
    ]
    return FredSearchOutput(
        results=results,
        query=query,
        total_results=data.get("count", len(results)),
    )

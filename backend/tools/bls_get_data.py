from __future__ import annotations

import logging
from datetime import datetime

from backend.config import settings
from backend.tools._http import fetch_json
from backend.tools.schemas import BlsGetDataOutput, BlsObservation, BlsSeriesData

logger = logging.getLogger(__name__)

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


async def bls_get_data(
    series_ids: list[str], start_year: str = "2020"
) -> BlsGetDataOutput:
    """Fetch employment, wage, and price data from the BLS API."""
    if len(series_ids) > 50:
        raise ValueError("BLS API allows a maximum of 50 series per request")

    end_year = str(datetime.now().year)

    body: dict = {
        "seriesid": series_ids,
        "startyear": start_year,
        "endyear": end_year,
    }
    if settings.bls_api_key:
        body["registrationkey"] = settings.bls_api_key
    else:
        logger.warning(
            "BLS_API_KEY not set. Using unregistered access (25 requests/day limit)."
        )

    data = await fetch_json(BLS_API_URL, method="POST", json_body=body)

    results = []
    for series in data.get("Results", {}).get("series", []):
        sid = series.get("seriesID", "")
        observations = [
            BlsObservation(
                year=d["year"],
                period=d["period"],
                value=d["value"],
                pct_change=d.get("calculations", {})
                .get("pct_changes", {})
                .get("1", None),
            )
            for d in series.get("data", [])[:20]
        ]
        results.append(BlsSeriesData(series_id=sid, data=observations))

    return BlsGetDataOutput(results=results)

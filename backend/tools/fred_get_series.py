from __future__ import annotations

import asyncio

from backend.config import settings
from backend.tools._http import fetch_json
from backend.tools.schemas import FredObservation, FredSeriesOutput

FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series"
FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"


async def fred_get_series(
    series_id: str, start_date: str = "2019-01-01"
) -> FredSeriesOutput:
    """Fetch metadata and recent observations for a FRED series."""
    common = {"api_key": settings.fred_api_key, "file_type": "json"}

    meta_params = {"series_id": series_id, **common}
    obs_params = {
        "series_id": series_id,
        "observation_start": start_date,
        "sort_order": "desc",
        "limit": 12,
        **common,
    }

    meta_data, obs_data = await asyncio.gather(
        fetch_json(FRED_SERIES_URL, params=meta_params),
        fetch_json(FRED_OBS_URL, params=obs_params),
    )

    # Metadata
    series_info = meta_data.get("seriess", [{}])[0]
    title = series_info.get("title", "")
    units = series_info.get("units", "")
    frequency = series_info.get("frequency", "")

    # Observations (reverse to chronological order)
    raw_obs = obs_data.get("observations", [])
    raw_obs.reverse()

    observations = [
        FredObservation(
            date=o["date"],
            value=o["value"] if o["value"] != "." else None,
        )
        for o in raw_obs
    ]

    latest_value = None
    latest_date = None
    if observations:
        last = observations[-1]
        latest_value = last.value
        latest_date = last.date

    return FredSeriesOutput(
        series_id=series_id,
        title=title,
        units=units,
        frequency=frequency,
        latest_value=latest_value,
        latest_date=latest_date,
        recent_observations=observations,
        total_observations=obs_data.get("count", len(observations)),
    )

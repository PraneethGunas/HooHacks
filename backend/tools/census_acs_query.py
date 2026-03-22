from __future__ import annotations

from backend.config import settings
from backend.tools._http import fetch_json
from backend.tools.schemas import CensusACSOutput


async def census_acs_query(
    table_variables: list[str],
    geography: str,
    state_fips: str = "51",
    year: int = 2023,
    dataset: str = "acs5",
) -> CensusACSOutput:
    """Query Census ACS for housing, income, and demographic data by geography.

    Args:
        table_variables: ACS variable codes, e.g. ["B25064_001E"] for median gross rent.
        geography: Census geography spec, e.g. "county:*" or "county:013".
        state_fips: State FIPS code, e.g. "51" for Virginia.
        year: ACS survey year (default 2023).
        dataset: "acs5" (all areas) or "acs1" (areas >65K pop).
    """
    base_url = f"https://api.census.gov/data/{year}/acs/{dataset}"

    # NAME gives the geography label alongside the data
    get_vars = ["NAME"] + table_variables

    params: dict = {
        "get": ",".join(get_vars),
        "for": geography,
        "key": settings.census_api_key,
    }
    # Only add state filter for sub-state geographies (county, tract, etc.)
    # Skip for state-level, national, or when state_fips is empty
    skip_state_filter = (
        not state_fips
        or "state" in geography
        or "us" in geography.lower()
        or "nation" in geography.lower()
    )
    if not skip_state_filter:
        params["in"] = f"state:{state_fips}"

    data = await fetch_json(base_url, params=params)

    # Census API returns list-of-lists: first row = headers, rest = data rows
    if not data or len(data) < 2:
        return CensusACSOutput(
            headers=[],
            rows=[],
            geography=geography,
            year=year,
            variables_requested=table_variables,
        )

    headers = data[0]
    rows = data[1:]

    return CensusACSOutput(
        headers=headers,
        rows=rows,
        geography=geography,
        year=year,
        variables_requested=table_variables,
    )

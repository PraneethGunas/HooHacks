from __future__ import annotations

import json

from langchain_core.tools import tool

from backend.tools import (
    census_acs_query as _census_acs_query,
    bea_regional_data as _bea_regional_data,
    hud_data as _hud_data,
    code_execute as _code_execute,
)

# Reuse existing wrappers from the analyst agent
from backend.agents.tool_wrappers import (
    fred_search,
    fred_get_series,
    bls_get_data,
    web_search_news,
    fetch_document_text,
    search_openalex,
    _error_json,
)


# ---------------------------------------------------------------------------
# Housing-specific tool wrappers
# ---------------------------------------------------------------------------


@tool
async def census_acs_query(
    table_variables: list[str],
    geography: str,
    state_fips: str = "51",
    year: int = 2023,
    dataset: str = "acs5",
) -> str:
    """Query Census ACS for local housing data — rent, home values, cost burden, income, tenure.

    Key tables: B25064_001E (median rent), B25077_001E (median home value),
    B25070_001E (rent as % income), B19013_001E (median income), B25003_001E (tenure total).

    geography examples:
    - 'county:*' with state_fips='51' → all Virginia counties
    - 'county:059' with state_fips='51' → Fairfax County, VA
    - 'state:06' with state_fips='' → California (state-level, no state filter)
    - 'state:*' with state_fips='' → all states

    IMPORTANT: For state-level queries, set state_fips to empty string ''.
    The 'in state:XX' filter only applies when querying within a state (county, tract)."""
    try:
        result = await _census_acs_query(
            table_variables=table_variables,
            geography=geography,
            state_fips=state_fips,
            year=year,
            dataset=dataset,
        )
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("census_acs_query", e)


@tool
async def bea_regional_data(
    table_name: str,
    geo_fips: str,
    year: str = "2023",
    line_code: str = "1",
) -> str:
    """Fetch BEA regional data — price parities, personal income by county/state.
    Key tables: SARPP (state price parities, line_code=1 for all items, 2 for rents),
    MARPP (metro price parities), CAINC1 (personal income).
    geo_fips: '51000' for Virginia, '51013' for Arlington County."""
    try:
        result = await _bea_regional_data(
            table_name=table_name,
            geo_fips=geo_fips,
            year=year,
            line_code=line_code,
        )
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("bea_regional_data", e)


@tool
async def hud_data(
    dataset: str,
    entity_id: str,
    year: int = 2025,
    quarter: int | None = None,
) -> str:
    """Fetch HUD housing data — Fair Market Rents (fmr), Income Limits (il), USPS vacancy (usps).

    entity_id formats:
    - State-level: 'VA', 'CA', 'TX' (2-letter state abbreviation)
    - County: '5101399999' for Arlington County VA (10-digit: state FIPS + county FIPS + 99999)
    - Metro: 'METRO47900M47900' for Washington-Arlington-Alexandria MSA

    FMR returns benchmark rents by bedroom count (0BR through 4BR).
    Income Limits returns low/very-low/extremely-low income thresholds."""
    try:
        result = await _hud_data(
            dataset=dataset,
            entity_id=entity_id,
            year=year,
            quarter=quarter,
        )
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("hud_data", e)


@tool
async def code_execute(code: str) -> str:
    """Execute Python code for housing calculations — mortgage payments, rent
    elasticities, affordability ratios, dollar impact estimates. Available: math,
    statistics, json, Decimal. Assign your answer to a variable named `result`.
    Example: result = round(1800 / (55000/12) * 100, 1)  # rent-to-income %"""
    try:
        result = await _code_execute(code=code)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("code_execute", e)


# ---------------------------------------------------------------------------
# Phase-to-tool mapping
# ---------------------------------------------------------------------------

HOUSING_PHASE_1_TOOLS = []  # No tools — reasoning from briefing

HOUSING_PHASE_2_TOOLS = [
    fred_search,
    fred_get_series,
    bls_get_data,
    census_acs_query,
    bea_regional_data,
    hud_data,
    web_search_news,
]

HOUSING_PHASE_3_TOOLS = [
    code_execute,
    fred_get_series,
    bls_get_data,
    census_acs_query,
    hud_data,
]

HOUSING_PHASE_4_TOOLS = [
    code_execute,
]

HOUSING_PHASE_5_TOOLS = [
    code_execute,
]

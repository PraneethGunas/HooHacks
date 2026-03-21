from __future__ import annotations

import json
import traceback

from langchain_core.tools import tool

from backend.tools import (
    fred_search as _fred_search,
    fred_get_series as _fred_get_series,
    bls_get_data as _bls_get_data,
    search_academic_papers as _search_academic_papers,
    search_openalex as _search_openalex,
    search_cbo_reports as _search_cbo_reports,
    web_search_news as _web_search_news,
    fetch_document_text as _fetch_document_text,
)


# ---------------------------------------------------------------------------
# Error-safe wrapper helper
# ---------------------------------------------------------------------------


def _error_json(tool_name: str, error: Exception) -> str:
    """Return a JSON error message the LLM can read and self-correct from."""
    return json.dumps(
        {
            "error": True,
            "tool": tool_name,
            "message": str(error),
            "hint": "Check your arguments and try again, or use a different tool/query.",
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# LangChain tool wrappers
# Each wraps our async Pydantic-returning tool → JSON string for the LLM
# Errors are caught and returned as JSON so the LLM can self-correct
# ---------------------------------------------------------------------------


@tool
async def fred_search(query: str, limit: int = 5) -> str:
    """Search FRED for economic data series by keyword. Returns series IDs,
    titles, units, and frequencies. Use to discover which FRED series exist
    for a given economic indicator before calling fred_get_series."""
    try:
        result = await _fred_search(query=query, limit=limit)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("fred_search", e)


@tool
async def fred_get_series(series_id: str, start_date: str = "2019-01-01") -> str:
    """Fetch numerical time series data for a known FRED series ID.
    Returns the most recent 12 data points plus metadata (title, units).
    Use AFTER fred_search to get actual numbers. Common IDs: FEDMINNFRWG
    (federal min wage), UNRATE (unemployment), CPIAUCSL (CPI)."""
    try:
        result = await _fred_get_series(series_id=series_id, start_date=start_date)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("fred_get_series", e)


@tool
async def bls_get_data(series_ids: list[str], start_year: str = "2020") -> str:
    """Fetch employment, wage, and price data from the Bureau of Labor Statistics.
    More granular than FRED — industry-specific employment, state-level labor force data.
    Max 50 series per call. Series ID patterns: CEU[industry]01 for employment,
    LAUST[fips]0000000000003 for state unemployment rate."""
    try:
        result = await _bls_get_data(series_ids=series_ids, start_year=start_year)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("bls_get_data", e)


@tool
async def search_academic_papers(
    query: str, year_range: str = "2015-2026", limit: int = 5
) -> str:
    """Search Semantic Scholar for peer-reviewed economics research.
    Returns titles, abstracts, TLDRs, citation counts. Prioritize
    highly-cited papers and meta-analyses. Cross-reference with search_openalex."""
    try:
        result = await _search_academic_papers(
            query=query, year_range=year_range, limit=limit
        )
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("search_academic_papers", e)


@tool
async def search_openalex(
    query: str, sort_by: str = "relevance_score", limit: int = 5
) -> str:
    """Search OpenAlex for economics and social science academic works. Better
    coverage for NBER working papers, Fed research, World Bank reports.
    Provides open_access_url for full text. Default sorts by relevance.
    Use sort_by='cited_by_count' to find landmark papers instead."""
    try:
        result = await _search_openalex(query=query, sort_by=sort_by, limit=limit)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("search_openalex", e)


@tool
async def search_cbo_reports(query: str, limit: int = 5) -> str:
    """Search the Congressional Budget Office for official policy analysis reports.
    CBO produces authoritative nonpartisan impact analyses, cost estimates,
    and employment projections for federal policy."""
    try:
        result = await _search_cbo_reports(query=query, limit=limit)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("search_cbo_reports", e)


@tool
async def web_search_news(query: str, recency: str = "past_month") -> str:
    """Search the web for recent news, policy proposals, and real-world outcomes.
    recency options: past_week, past_month, past_year.
    Use to find current legislative status or outcomes from analogous policies."""
    try:
        result = await _web_search_news(query=query, recency=recency)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("web_search_news", e)


@tool
async def fetch_document_text(url: str, max_chars: int = 4000) -> str:
    """Fetch and extract readable text from a URL (HTML or PDF). Use AFTER a
    search tool finds a relevant document you need to read in full.
    Increase max_chars to 8000-10000 for long CBO reports."""
    try:
        result = await _fetch_document_text(url=url, max_chars=max_chars)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return _error_json("fetch_document_text", e)


# ---------------------------------------------------------------------------
# Phase-to-tool mapping
# ---------------------------------------------------------------------------

PHASE_1_TOOLS = [web_search_news, fetch_document_text, fred_get_series]
PHASE_2_TOOLS = [fred_search, fred_get_series, bls_get_data]
PHASE_3_TOOLS = []  # No tools — pure reasoning
PHASE_4_TOOLS = [
    search_academic_papers,
    search_openalex,
    search_cbo_reports,
    fetch_document_text,
    web_search_news,
]
PHASE_5_TOOLS = []  # No tools — synthesis only

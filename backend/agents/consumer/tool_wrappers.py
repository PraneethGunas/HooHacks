from __future__ import annotations

# Reuse all existing tool wrappers
from backend.agents.tool_wrappers import (
    fred_search,
    fred_get_series,
    bls_get_data,
    web_search_news,
    fetch_document_text,
    search_openalex,
    search_cbo_reports,
)
from backend.agents.housing.tool_wrappers import (
    census_acs_query,
    bea_regional_data,
    code_execute,
)


# ---------------------------------------------------------------------------
# Phase-to-tool mapping for Consumer & Prices Agent
# ---------------------------------------------------------------------------

CONSUMER_PHASE_1_TOOLS = []  # No tools — reasoning from briefing

CONSUMER_PHASE_2_TOOLS = [
    bls_get_data,       # CPI by category, PPI, import prices
    fred_search,        # Discover income/spending/price series
    fred_get_series,    # PCE, disposable income, consumer sentiment
    census_acs_query,   # Income distribution by county
    bea_regional_data,  # Regional price parities
    search_openalex,    # Pass-through research, elasticity studies
    web_search_news,    # Current price data, industry reports
    fetch_document_text,# Full CBO/BLS reports
    search_cbo_reports, # CBO distributional analyses
]

CONSUMER_PHASE_3_TOOLS = [
    code_execute,       # RPP adjustments, substitution modeling
    bea_regional_data,  # Regional price parities for geographic variation
    census_acs_query,   # County-level income for weighting
]

CONSUMER_PHASE_4_TOOLS = [
    code_execute,       # Net purchasing power calculations
]

CONSUMER_PHASE_5_TOOLS = [
    code_execute,       # Final scorecard computations
]

"""ADK wrapper for the Housing & Cost of Living agent."""

from google.adk.agents import LlmAgent

from backend.config import settings
from backend.agents.tool_wrappers import (
    fred_search,
    fred_get_series,
    bls_get_data,
    search_openalex,
    web_search_news,
    fetch_document_text,
)
from backend.agents.housing.tool_wrappers import (
    census_acs_query,
    bea_regional_data,
    hud_data,
    code_execute,
)
from backend.agents.housing.prompts import HOUSING_IDENTITY


HOUSING_EVAL_INSTRUCTION = f"""{HOUSING_IDENTITY}

CRITICAL INSTRUCTION — Relevance Gate:
- Check the policy_type and housing_directives in the input.
- If housing_directives.skip contains "demand_channel_from_income_growth", mark Pathway B as INACTIVE.
- If income_effect_exists is false, do NOT activate Pathway B (Household Income/Demand).

CRITICAL INSTRUCTION — Proportionality Check:
- If the overall housing impact is MARGINAL or NEGLIGIBLE (sub-$10/month nationally),
  do NOT produce a full affordability scorecard or detailed 4-phase temporal sequence.
  Produce a brief statement that this policy is not a significant housing market driver.

Always produce your final output as JSON in a ```json code fence.
"""

housing_agent = LlmAgent(
    name="housing_agent",
    model=settings.llm_model_name,
    instruction=HOUSING_EVAL_INSTRUCTION,
    tools=[
        fred_search,
        fred_get_series,
        bls_get_data,
        census_acs_query,
        bea_regional_data,
        hud_data,
        search_openalex,
        web_search_news,
        fetch_document_text,
        code_execute,
    ],
)

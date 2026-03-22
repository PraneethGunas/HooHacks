"""ADK wrapper for the Consumer & Prices agent."""

from google.adk.agents import LlmAgent

from backend.config import settings
from backend.agents.tool_wrappers import (
    fred_search,
    fred_get_series,
    bls_get_data,
    search_openalex,
    search_cbo_reports,
    web_search_news,
    fetch_document_text,
)
from backend.agents.housing.tool_wrappers import (
    census_acs_query,
    bea_regional_data,
    code_execute,
)
from backend.agents.consumer.prompts import CONSUMER_IDENTITY


CONSUMER_EVAL_INSTRUCTION = f"""{CONSUMER_IDENTITY}

CRITICAL INSTRUCTION — Income Gate:
- If the user message says "Income effect exists: FALSE" or "Policy type: REGULATORY_COST",
  you MUST operate in MODE B (pure cost analysis).
- In MODE B: set income change to $0 for ALL household profiles. Do NOT mention wage ripple,
  wage compression, or wage increase. Do NOT claim any household is "better off".
  Frame impact as pure cost increase. Label burden as regressive or proportional.
- If "Income effect exists: TRUE", operate in MODE A (bilateral analysis) with both income
  and cost sides.

Always produce your final output as JSON in a ```json code fence.
"""

consumer_agent = LlmAgent(
    name="consumer_agent",
    model=settings.llm_model_name,
    instruction=CONSUMER_EVAL_INSTRUCTION,
    tools=[
        bls_get_data,
        fred_search,
        fred_get_series,
        census_acs_query,
        bea_regional_data,
        search_openalex,
        web_search_news,
        fetch_document_text,
        search_cbo_reports,
        code_execute,
    ],
)

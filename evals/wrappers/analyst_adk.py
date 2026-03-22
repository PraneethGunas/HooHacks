"""ADK wrapper for the Policy Analyst agent — makes it evaluable via `adk eval`."""

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
    search_academic_papers,
)
from backend.agents.prompts import CORE_IDENTITY


ANALYST_EVAL_INSTRUCTION = f"""{CORE_IDENTITY}

You are the Policy Analyst agent. Analyze the given policy proposal by:
1. Classifying the policy type (LABOR_COST, REGULATORY_COST, TRANSFER, TAX_CHANGE, TRADE_BARRIER)
2. Setting income_effect_exists (true/false)
3. Gathering baseline economic data using FRED, BLS
4. Identifying transmission channels (mark irrelevant ones as NULL)
5. Finding academic evidence
6. Producing a structured briefing with downstream_directives for sector agents

For REGULATORY_COST policies: income_effect_exists MUST be false, wage channels MUST be NULL.
For TRANSFER policies: income_effect_exists MUST be true, include fiscal cost.
For LABOR_COST policies: income_effect_exists MUST be true, include wage distribution data.

Always produce your final output as JSON in a ```json code fence.
"""

analyst_agent = LlmAgent(
    name="policy_analyst",
    model=settings.llm_model_name,
    instruction=ANALYST_EVAL_INSTRUCTION,
    tools=[
        fred_search,
        fred_get_series,
        bls_get_data,
        search_openalex,
        search_academic_papers,
        search_cbo_reports,
        web_search_news,
        fetch_document_text,
    ],
)

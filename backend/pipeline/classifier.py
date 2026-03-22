"""
Stage 0: Classifier — routes the user query and extracts policy parameters.

Uses a fast/cheap LLM model. Falls back to keyword matching for the 3 demo scenarios.
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from backend.pipeline.orchestrator import PipelineState
from backend.pipeline.llm import llm_chat, parse_json_response

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]

# ---------------------------------------------------------------------------
# Keyword fallback for when no LLM key is configured
# ---------------------------------------------------------------------------
DEMO_CLASSIFICATIONS = {
    "h1b": {
        "policy_type": "immigration",
        "policy_name": "H-1B Visa Policy Reform",
        "parameters": {
            "visa_type": "H-1B",
            "affected_group": "international students and skilled workers",
            "policy_area": "immigration and employment",
        },
        "affected_populations": [
            "international students",
            "H-1B visa holders",
            "tech employers",
            "domestic STEM workers",
        ],
    },
    "student_loan": {
        "policy_type": "education_finance",
        "policy_name": "Student Loan Forgiveness Plan",
        "parameters": {
            "program_type": "loan forgiveness",
            "target_debt": "$50,000",
            "affected_group": "recent graduates",
            "policy_area": "higher education finance",
        },
        "affected_populations": [
            "2026 graduates",
            "federal loan borrowers",
            "universities",
            "taxpayers",
        ],
    },
    "tariff": {
        "policy_type": "trade",
        "policy_name": "Electronics Import Tariff",
        "parameters": {
            "tariff_target": "electronics from China",
            "affected_sector": "electronics import/retail",
            "policy_area": "international trade",
        },
        "affected_populations": [
            "small electronics importers",
            "consumers",
            "domestic manufacturers",
            "retail workers",
        ],
    },
}

SCENARIO_KEYWORDS = {
    "h1b": ["h1b", "h-1b", "visa", "immigration", "international student"],
    "student_loan": ["student loan", "loan forgiveness", "student debt", "tuition"],
    "tariff": ["tariff", "import", "trade", "electronics from china"],
}


def _keyword_classify(query: str) -> dict[str, Any] | None:
    q = query.lower()
    for scenario, keywords in SCENARIO_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return DEMO_CLASSIFICATIONS[scenario]
    return None


CLASSIFIER_SYSTEM = """You are a policy classification engine. Given a user's policy question,
extract structured parameters. Respond with JSON only.

Required fields:
{
  "policy_type": "immigration|trade|education_finance|labor|housing|healthcare|tax|other",
  "policy_name": "Short name for the policy",
  "parameters": { ... key policy parameters extracted from the query ... },
  "affected_populations": ["list", "of", "affected", "groups"]
}"""


async def run_classifier(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 0: Classify the query and extract policy parameters."""
    await emit({
        "type": "agent_start",
        "agent": "classifier",
        "data": {"query": state.query},
    })

    result = None

    # Try LLM classification first
    try:
        raw = await llm_chat(
            system_prompt=CLASSIFIER_SYSTEM,
            user_prompt=f"Policy question: {state.query}\n\nUser context: {json.dumps(state.user_context)}",
            json_mode=True,
            fast=True,
        )
        if raw:
            result = parse_json_response(raw)
    except Exception:
        pass

    # Fall back to keyword matching
    if not result:
        result = _keyword_classify(state.query)

    # Last resort: generic classification
    if not result:
        result = {
            "policy_type": "other",
            "policy_name": "Policy Analysis",
            "parameters": {"query": state.query},
            "affected_populations": ["general public"],
        }

    state.policy_type = result.get("policy_type", "other")
    state.policy_params = result

    # Emit both backend and frontend event shapes for compatibility
    frontend_data = {
        # Frontend-expected fields
        "task_type": result.get("policy_type", "other"),
        "policy_params": {
            "jurisdiction": "US",  # Default to US if not specified
            **result.get("parameters", {}),
        },
        "affected_sectors": ["labor", "housing", "consumer", "business"],
        "extracted_tags": result.get("affected_populations", []),
        # Keep backend fields for backward compat
        "policy_type": result.get("policy_type", "other"),
        "policy_name": result.get("policy_name", ""),
        "parameters": result.get("parameters", {}),
        "affected_populations": result.get("affected_populations", []),
    }

    await emit({
        "type": "classifier_complete",
        "agent": "classifier",
        "data": frontend_data,
    })

    return state

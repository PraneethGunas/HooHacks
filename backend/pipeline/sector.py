"""
Stage 2: Sector Agents — 4 parallel agents with real tool calls + LLM analysis.

Each sector agent:
  1. Fetches sector-specific data from real APIs (FRED, BLS)
  2. Runs elasticity calculations and scenario projections
  3. Feeds enriched data + briefing into an LLM for structured analysis
  4. Emits tool_call events so the frontend shows live activity per agent

===========================================================================
INTEGRATION GUIDE
===========================================================================
OWNER: Rudra — swap with LangGraph ReAct agents if time permits.

Each agent now makes 2-4 real tool calls before its LLM reasoning step.
Tool calls are sector-specific and policy-aware.
===========================================================================
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from typing import Any, Awaitable, Callable

from backend.models.pipeline import (
    CausalClaim,
    ConfidenceLevel,
    SectorReport,
    ToolCallRecord,
)
from backend.pipeline.orchestrator import PipelineState
from backend.pipeline.llm import llm_chat, parse_json_response

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]

SECTORS = ["labor", "housing", "consumer", "business"]

# ---------------------------------------------------------------------------
# Sector-specific tool call strategies
# ---------------------------------------------------------------------------
# Each sector defines which FRED series, BLS series, and computations to run.
# These adapt based on policy_type from the classifier.

SECTOR_TOOLS: dict[str, dict[str, list[dict[str, Any]]]] = {
    "labor": {
        "default": [
            {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}, "label": "Unemployment rate"},
            {"tool": "fred_get_series", "args": {"series_id": "PAYEMS"}, "label": "Total nonfarm payrolls"},
            {"tool": "bls_get_data", "args": {"series_ids": ["CES0500000003"]}, "label": "Average hourly earnings"},
            {"tool": "elasticity", "args": {"x_series": "FEDMINNFRWG", "y_series": "UNRATE"}, "label": "Min wage → unemployment elasticity"},
        ],
        "immigration": [
            {"tool": "fred_get_series", "args": {"series_id": "LNS12300060"}, "label": "Employment-population ratio (25-54)"},
            {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}, "label": "Unemployment rate"},
            {"tool": "bls_get_data", "args": {"series_ids": ["CES0500000003"]}, "label": "Average hourly earnings (private)"},
            {"tool": "scenario", "args": {"variable": "tech_employment", "baseline": 6.2, "shock": -5.0, "elasticity": 0.3}, "label": "H1B restriction → tech employment scenario"},
        ],
        "student_loan": [
            {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}, "label": "Unemployment rate"},
            {"tool": "fred_get_series", "args": {"series_id": "LNS12300060"}, "label": "Employment-population ratio (25-54)"},
            {"tool": "bls_get_data", "args": {"series_ids": ["CES6500000003"]}, "label": "Education sector earnings"},
        ],
        "tariff": [
            {"tool": "fred_get_series", "args": {"series_id": "MANEMP"}, "label": "Manufacturing employment"},
            {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}, "label": "Unemployment rate"},
            {"tool": "bls_get_data", "args": {"series_ids": ["CES3000000003"]}, "label": "Manufacturing hourly earnings"},
            {"tool": "scenario", "args": {"variable": "manufacturing_jobs", "baseline": 12.8, "shock": 3.0, "elasticity": 0.15}, "label": "Tariff → manufacturing jobs scenario"},
        ],
    },
    "housing": {
        "default": [
            {"tool": "fred_get_series", "args": {"series_id": "MSPUS"}, "label": "Median home sales price"},
            {"tool": "fred_get_series", "args": {"series_id": "MORTGAGE30US"}, "label": "30-year mortgage rate"},
            {"tool": "fred_get_series", "args": {"series_id": "RRVRUSQ156N"}, "label": "Rental vacancy rate"},
            {"tool": "census_acs_query", "args": {"table_variables": ["B25064_001E"], "geography": "state:*"}, "label": "Census ACS: median gross rent by state"},
            {"tool": "hud_data", "args": {"dataset": "fmr", "entity_id": "VA"}, "label": "HUD Fair Market Rents (Virginia)"},
        ],
        "immigration": [
            {"tool": "fred_get_series", "args": {"series_id": "MSPUS"}, "label": "Median home sales price"},
            {"tool": "fred_get_series", "args": {"series_id": "RRVRUSQ156N"}, "label": "Rental vacancy rate"},
            {"tool": "census_acs_query", "args": {"table_variables": ["B25064_001E", "B25077_001E"], "geography": "state:*"}, "label": "Census ACS: median rent & home value by state"},
            {"tool": "scenario", "args": {"variable": "rent_index", "baseline": 100.0, "shock": -2.0, "elasticity": 0.4}, "label": "H1B restriction → rental demand scenario"},
        ],
        "student_loan": [
            {"tool": "fred_get_series", "args": {"series_id": "MSPUS"}, "label": "Median home sales price"},
            {"tool": "fred_get_series", "args": {"series_id": "MORTGAGE30US"}, "label": "30-year mortgage rate"},
            {"tool": "census_acs_query", "args": {"table_variables": ["B25077_001E"], "geography": "state:*"}, "label": "Census ACS: median home value by state"},
            {"tool": "scenario", "args": {"variable": "first_time_buyers", "baseline": 26.0, "shock": 15.0, "elasticity": 0.25}, "label": "Loan forgiveness → first-time buyer share scenario"},
        ],
        "tariff": [
            {"tool": "fred_get_series", "args": {"series_id": "WPUSI012011"}, "label": "PPI: construction materials"},
            {"tool": "fred_get_series", "args": {"series_id": "MSPUS"}, "label": "Median home sales price"},
            {"tool": "hud_data", "args": {"dataset": "fmr", "entity_id": "VA"}, "label": "HUD Fair Market Rents (Virginia)"},
            {"tool": "scenario", "args": {"variable": "construction_costs", "baseline": 100.0, "shock": 8.0, "elasticity": 0.6}, "label": "Tariff → construction cost scenario"},
        ],
    },
    "consumer": {
        "default": [
            {"tool": "fred_get_series", "args": {"series_id": "CPIAUCSL"}, "label": "Consumer Price Index"},
            {"tool": "fred_get_series", "args": {"series_id": "PCE"}, "label": "Personal consumption expenditures"},
            {"tool": "fred_get_series", "args": {"series_id": "DSPIC96"}, "label": "Real disposable personal income"},
        ],
        "immigration": [
            {"tool": "fred_get_series", "args": {"series_id": "CPIAUCSL"}, "label": "Consumer Price Index"},
            {"tool": "fred_get_series", "args": {"series_id": "PCE"}, "label": "Personal consumption expenditures"},
            {"tool": "scenario", "args": {"variable": "tech_service_prices", "baseline": 100.0, "shock": 3.0, "elasticity": 0.5}, "label": "H1B restriction → tech service price scenario"},
        ],
        "student_loan": [
            {"tool": "fred_get_series", "args": {"series_id": "CPIAUCSL"}, "label": "Consumer Price Index"},
            {"tool": "fred_get_series", "args": {"series_id": "TOTALSL"}, "label": "Total student loans outstanding"},
            {"tool": "fred_get_series", "args": {"series_id": "PCE"}, "label": "Personal consumption expenditures"},
            {"tool": "scenario", "args": {"variable": "consumer_spending", "baseline": 18.9, "shock": 2.5, "elasticity": 0.7}, "label": "Loan forgiveness → consumer spending boost scenario"},
        ],
        "tariff": [
            {"tool": "fred_get_series", "args": {"series_id": "CPIAUCSL"}, "label": "Consumer Price Index"},
            {"tool": "fred_get_series", "args": {"series_id": "PCE"}, "label": "Personal consumption expenditures"},
            {"tool": "fred_get_series", "args": {"series_id": "DSPIC96"}, "label": "Real disposable personal income"},
            {"tool": "scenario", "args": {"variable": "electronics_prices", "baseline": 100.0, "shock": 15.0, "elasticity": 0.8}, "label": "Tariff → electronics price scenario"},
        ],
    },
    "business": {
        "default": [
            {"tool": "fred_get_series", "args": {"series_id": "BUSLOANS"}, "label": "Commercial & industrial loans"},
            {"tool": "fred_get_series", "args": {"series_id": "INDPRO"}, "label": "Industrial production index"},
            {"tool": "bls_get_data", "args": {"series_ids": ["PRS85006092"]}, "label": "Business sector: unit labor costs"},
        ],
        "immigration": [
            {"tool": "fred_get_series", "args": {"series_id": "INDPRO"}, "label": "Industrial production index"},
            {"tool": "fred_get_series", "args": {"series_id": "BUSLOANS"}, "label": "Commercial & industrial loans"},
            {"tool": "scenario", "args": {"variable": "tech_labor_costs", "baseline": 100.0, "shock": 8.0, "elasticity": 0.6}, "label": "H1B restriction → tech labor cost scenario"},
        ],
        "student_loan": [
            {"tool": "fred_get_series", "args": {"series_id": "BUSLOANS"}, "label": "Commercial & industrial loans"},
            {"tool": "fred_get_series", "args": {"series_id": "RSAFS"}, "label": "Retail sales"},
            {"tool": "scenario", "args": {"variable": "retail_revenue", "baseline": 7.2, "shock": 2.0, "elasticity": 0.5}, "label": "Loan forgiveness → retail revenue scenario"},
        ],
        "tariff": [
            {"tool": "fred_get_series", "args": {"series_id": "INDPRO"}, "label": "Industrial production index"},
            {"tool": "fred_get_series", "args": {"series_id": "BOPGSTB"}, "label": "Trade balance: goods and services"},
            {"tool": "bls_get_data", "args": {"series_ids": ["PRS85006092"]}, "label": "Business sector: unit labor costs"},
            {"tool": "scenario", "args": {"variable": "import_costs", "baseline": 100.0, "shock": 25.0, "elasticity": 0.7}, "label": "Tariff → import cost scenario"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Tool execution helpers
# ---------------------------------------------------------------------------

async def _execute_tool(
    tool_spec: dict[str, Any],
    sector: str,
    emit: EventCallback,
) -> dict[str, Any]:
    """Execute a single tool and emit a tool_call event."""
    tool_name = tool_spec["tool"]
    args = tool_spec["args"]
    label = tool_spec.get("label", tool_name)

    await emit({
        "type": "sector_agent_tool_call",
        "agent": sector,
        "data": {
            "agent": sector.title(),
            "tool": tool_name,
            "query": label,
        },
    })

    try:
        if tool_name == "fred_get_series":
            from backend.tools.fred_get_series import fred_get_series
            result = await fred_get_series(**args)
            return {"tool": tool_name, "label": label, "data": result.model_dump()}

        elif tool_name == "bls_get_data":
            from backend.tools.bls_get_data import bls_get_data
            result = await bls_get_data(**args)
            return {"tool": tool_name, "label": label, "data": result.model_dump()}

        elif tool_name == "elasticity":
            from backend.tools.calculate_elasticity import calculate_elasticity
            from backend.tools.fred_get_series import fred_get_series as fred_get
            # Fetch both series and compute elasticity
            x_data = await fred_get(args["x_series"])
            y_data = await fred_get(args["y_series"])
            x_vals = [float(o.value) for o in x_data.recent_observations if o.value]
            y_vals = [float(o.value) for o in y_data.recent_observations if o.value]
            min_len = min(len(x_vals), len(y_vals))
            if min_len >= 3:
                result = calculate_elasticity(
                    x_vals[:min_len], y_vals[:min_len],
                    x_label=args["x_series"], y_label=args["y_series"],
                )
                return {"tool": "calculate_elasticity", "label": label, "data": result.to_dict()}
            return {"tool": "calculate_elasticity", "label": label, "data": {"error": "insufficient data points"}}

        elif tool_name == "scenario":
            from backend.tools.run_scenario_analysis import run_scenario_analysis
            result = run_scenario_analysis(
                variable_name=args["variable"],
                baseline_value=args["baseline"],
                shock_pct=args["shock"],
                elasticity=args["elasticity"],
            )
            return {"tool": "run_scenario_analysis", "label": label, "data": result.to_dict()}

        elif tool_name == "census_acs_query":
            from backend.tools.census_acs_query import census_acs_query
            result = await census_acs_query(**args)
            return {"tool": tool_name, "label": label, "data": result.model_dump()}

        elif tool_name == "bea_regional_data":
            from backend.tools.bea_regional_data import bea_regional_data
            result = await bea_regional_data(**args)
            return {"tool": tool_name, "label": label, "data": result.model_dump()}

        elif tool_name == "hud_data":
            from backend.tools.hud_data import hud_data
            result = await hud_data(**args)
            return {"tool": tool_name, "label": label, "data": result.model_dump()}

        elif tool_name == "code_execute":
            from backend.tools.code_execute import code_execute
            result = await code_execute(**args)
            return {"tool": tool_name, "label": label, "data": result.model_dump()}

        else:
            return {"tool": tool_name, "label": label, "data": {"error": f"unknown tool: {tool_name}"}}

    except Exception as e:
        logger.warning(f"Sector {sector} tool {tool_name} failed: {e}")
        return {"tool": tool_name, "label": label, "data": {"error": str(e)}}


async def _run_sector_tools(
    sector: str,
    policy_type: str,
    emit: EventCallback,
) -> list[dict[str, Any]]:
    """Run all tools for a sector based on policy type."""
    sector_tools = SECTOR_TOOLS.get(sector, {})
    tools_for_policy = sector_tools.get(policy_type, sector_tools.get("default", []))

    results = []
    for tool_spec in tools_for_policy:
        result = await _execute_tool(tool_spec, sector, emit)
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# System prompts for each sector agent
# ---------------------------------------------------------------------------

SECTOR_PROMPTS = {
    "labor": """You are the LABOR sector analyst in a multi-agent policy analysis system.
Your focus: employment, wages, workforce participation, job creation/destruction, labor mobility.

Given a policy briefing AND real economic data from government APIs, produce a structured analysis as JSON with this exact schema:
{
  "sector": "labor",
  "direct_effects": [<CausalClaim objects>],
  "second_order_effects": [<CausalClaim objects>],
  "feedback_loops": [<CausalClaim objects>],
  "cross_sector_dependencies": ["list of dependencies on other sectors"],
  "dissent": "optional dissenting view or null"
}

Each CausalClaim MUST have:
{
  "claim": "The assertion",
  "cause": "What drives this effect",
  "effect": "What changes",
  "mechanism": "HOW cause leads to effect — MANDATORY, be specific",
  "confidence": "empirical" | "theoretical" | "speculative",
  "evidence": ["citations from the briefing data AND the real data provided"],
  "assumptions": ["what you're taking as given"],
  "sensitivity": "if X changes, this conclusion breaks" or null
}

IMPORTANT: You have REAL government data (FRED, BLS) and computed elasticities/scenarios below.
- Use specific numbers from the data in your evidence fields
- EMPIRICAL claims MUST cite the actual data values
- Scenario projections (base/bull/bear) should inform your analysis
- Produce 2-4 direct effects, 1-3 second-order effects, 1-2 feedback loops""",

    "housing": """You are the HOUSING sector analyst in a multi-agent policy analysis system.
Your focus: housing demand, rent levels, home prices, geographic mobility, housing supply.

Given a policy briefing AND real economic data, produce a structured analysis as JSON with this exact schema:
{
  "sector": "housing",
  "direct_effects": [<CausalClaim objects>],
  "second_order_effects": [<CausalClaim objects>],
  "feedback_loops": [<CausalClaim objects>],
  "cross_sector_dependencies": ["dependencies on labor, consumer, business sectors"],
  "dissent": "optional dissenting view or null"
}

Each CausalClaim MUST have all fields: claim, cause, effect, mechanism (MANDATORY), confidence, evidence, assumptions, sensitivity.

IMPORTANT: Use the REAL government data (FRED series, computed scenarios) provided below.
Cite actual numbers. EMPIRICAL claims must reference specific data values.
Produce 2-4 direct, 1-3 second-order, 1-2 feedback loops.""",

    "consumer": """You are the CONSUMER sector analyst in a multi-agent policy analysis system.
Your focus: consumer prices, purchasing power, spending patterns, cost of living, inflation pass-through.

Given a policy briefing AND real economic data, produce a structured analysis as JSON with this exact schema:
{
  "sector": "consumer",
  "direct_effects": [<CausalClaim objects>],
  "second_order_effects": [<CausalClaim objects>],
  "feedback_loops": [<CausalClaim objects>],
  "cross_sector_dependencies": ["dependencies on labor, housing, business sectors"],
  "dissent": "optional dissenting view or null"
}

Each CausalClaim MUST have all fields: claim, cause, effect, mechanism (MANDATORY), confidence, evidence, assumptions, sensitivity.

IMPORTANT: Use the REAL government data (FRED series, computed scenarios) provided below.
Cite actual numbers. EMPIRICAL claims must reference specific data values.
Produce 2-4 direct, 1-3 second-order, 1-2 feedback loops.""",

    "business": """You are the BUSINESS sector analyst in a multi-agent policy analysis system.
Your focus: firm margins, business closures, automation incentives, regional disparities, market competition.

Given a policy briefing AND real economic data, produce a structured analysis as JSON with this exact schema:
{
  "sector": "business",
  "direct_effects": [<CausalClaim objects>],
  "second_order_effects": [<CausalClaim objects>],
  "feedback_loops": [<CausalClaim objects>],
  "cross_sector_dependencies": ["dependencies on labor, housing, consumer sectors"],
  "dissent": "optional dissenting view or null"
}

Each CausalClaim MUST have all fields: claim, cause, effect, mechanism (MANDATORY), confidence, evidence, assumptions, sensitivity.

IMPORTANT: Use the REAL government data (FRED series, computed scenarios) provided below.
Cite actual numbers. EMPIRICAL claims must reference specific data values.
Produce 2-4 direct, 1-3 second-order, 1-2 feedback loops.""",
}


# ---------------------------------------------------------------------------
# Error report (when LLM fails in production — no mock data)
# ---------------------------------------------------------------------------

def _error_report(sector: str, error_msg: str) -> SectorReport:
    """Create a SectorReport that clearly signals an LLM failure.

    Unlike _fallback_report(), this does NOT inject fake claims.
    The synthesis agent will see empty effects and the error in dissent,
    allowing it to handle the gap transparently.
    """
    return SectorReport(
        sector=sector,
        direct_effects=[],
        second_order_effects=[],
        feedback_loops=[],
        cross_sector_dependencies=[s for s in SECTORS if s != sector],
        dissent=f"⚠️ LLM ERROR — {sector} analysis unavailable: {error_msg}",
    )


# ---------------------------------------------------------------------------
# Fallback demo responses (ONLY for frontend Demo/mock flow)
# ---------------------------------------------------------------------------

def _fallback_report(sector: str, state: PipelineState) -> SectorReport:
    """Generate a minimal demo SectorReport without LLM.

    ⚠️  This should ONLY be called from the frontend mock/demo pipeline.
    It must NEVER be used as an automatic fallback in the production pipeline.
    """
    return SectorReport(
        sector=sector,
        direct_effects=[
            CausalClaim(
                claim=f"Policy directly affects {sector} sector",
                cause=state.policy_params.get("policy_name", "policy change"),
                effect=f"Changes in {sector} sector conditions",
                mechanism=f"Direct regulatory/economic channel affecting {sector} participants",
                confidence=ConfidenceLevel.THEORETICAL,
                evidence=[],
                assumptions=["Policy is implemented as described"],
            ),
        ],
        second_order_effects=[
            CausalClaim(
                claim=f"Ripple effects propagate through {sector} supply chains",
                cause=f"Initial {sector} disruption",
                effect="Adjustment in related markets",
                mechanism=f"Market participants in {sector} adjust behavior in response to changed incentives",
                confidence=ConfidenceLevel.SPECULATIVE,
                evidence=[],
                assumptions=["Markets adjust within 6-12 months"],
            ),
        ],
        feedback_loops=[],
        cross_sector_dependencies=[s for s in SECTORS if s != sector],
        dissent=None,
    )


def _normalize_confidence(raw_value: Any) -> ConfidenceLevel:
    """Map LLM confidence strings/numbers to our enum, handling creative LLM outputs."""
    # Handle numeric confidence (e.g. 0.8, 85, 0.3)
    if isinstance(raw_value, (int, float)):
        if raw_value > 1:
            raw_value = raw_value / 100  # treat 85 as 0.85
        if raw_value >= 0.7:
            return ConfidenceLevel.EMPIRICAL
        if raw_value >= 0.4:
            return ConfidenceLevel.THEORETICAL
        return ConfidenceLevel.SPECULATIVE

    if not isinstance(raw_value, str):
        return ConfidenceLevel.THEORETICAL

    v = raw_value.lower().strip()
    try:
        return ConfidenceLevel(v)
    except ValueError:
        pass
    if v in ("high", "strong", "data-backed", "data_backed", "evidence-based"):
        return ConfidenceLevel.EMPIRICAL
    if v in ("medium", "moderate", "model-based", "model_based"):
        return ConfidenceLevel.THEORETICAL
    if v in ("low", "weak", "uncertain", "unknown"):
        return ConfidenceLevel.SPECULATIVE
    return ConfidenceLevel.THEORETICAL


def _parse_sector_report(sector: str, raw: str, tool_records: list[ToolCallRecord] | None = None) -> SectorReport:
    """Parse LLM JSON output into a SectorReport."""
    try:
        data = parse_json_response(raw)
    except Exception as e:
        logger.error(f"Sector {sector}: JSON parse failed: {e}, raw[:500]={raw[:500]}")
        return SectorReport(sector=sector)

    # Gemini sometimes wraps the entire response in an array: [{...}]
    # Unwrap to get the dict inside
    if isinstance(data, list):
        logger.warning(f"Sector {sector}: parse_json_response returned a list (len={len(data)}), unwrapping")
        dicts = [item for item in data if isinstance(item, dict)]
        if dicts:
            data = dicts[0]
        else:
            logger.error(f"Sector {sector}: list contained no dicts, raw[:500]={raw[:500]}")
            return SectorReport(sector=sector)

    if not isinstance(data, dict):
        logger.error(f"Sector {sector}: parsed data is {type(data).__name__}, not dict. raw[:500]={raw[:500]}")
        return SectorReport(sector=sector)

    def _to_list(val: Any) -> list[str]:
        if isinstance(val, list):
            return [str(v) for v in val]
        if isinstance(val, str) and val:
            return [val]
        return []

    def _parse_claim(c: Any) -> CausalClaim | None:
        # If LLM returned a list instead of a dict, try to use the first dict element
        if isinstance(c, list):
            dicts = [item for item in c if isinstance(item, dict)]
            if dicts:
                c = dicts[0]
            else:
                return None
        if not isinstance(c, dict):
            return None
        return CausalClaim(
            claim=c.get("claim", ""),
            cause=c.get("cause", ""),
            effect=c.get("effect", ""),
            mechanism=c.get("mechanism", "unspecified"),
            confidence=_normalize_confidence(c.get("confidence", "speculative")),
            evidence=_to_list(c.get("evidence", [])),
            assumptions=_to_list(c.get("assumptions", [])),
            sensitivity=c.get("sensitivity"),
        )

    def _parse_claims(raw_list: Any) -> list[CausalClaim]:
        """Parse a list of claims, handling nested lists and non-dict items."""
        if not isinstance(raw_list, list):
            return []
        # Flatten one level of nesting: [[{...}, {...}]] → [{...}, {...}]
        flat: list[Any] = []
        for item in raw_list:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
        return [claim for c in flat if (claim := _parse_claim(c)) is not None]

    return SectorReport(
        sector=sector,
        direct_effects=_parse_claims(data.get("direct_effects", [])),
        second_order_effects=_parse_claims(data.get("second_order_effects", [])),
        feedback_loops=_parse_claims(data.get("feedback_loops", [])),
        cross_sector_dependencies=data.get("cross_sector_dependencies", []),
        dissent=data.get("dissent"),
        tool_calls_made=tool_records or [],
    )


async def _run_one_sector_single_shot(
    sector: str,
    state: PipelineState,
    emit: EventCallback,
) -> SectorReport:
    """Run a single sector agent via single-shot: tool calls → LLM analysis.

    Used for labor and business (no LangGraph agent yet).
    """
    await emit({
        "type": "sector_agent_started",
        "agent": sector,
        "data": {
            "sector": sector,
            "agent": sector.title(),
            "agent_mode": "single_shot",
        },
    })

    # Step 1: Run sector-specific tool calls
    policy_type = state.policy_params.get("policy_type", "default")
    tool_results = await _run_sector_tools(sector, policy_type, emit)

    # Build tool call records for the report
    tool_records = [
        ToolCallRecord(
            tool=tr["tool"],
            query=tr["label"],
            success="error" not in tr.get("data", {}),
            summary=json.dumps(tr["data"], default=str)[:500],
        )
        for tr in tool_results
    ]

    # Step 2: Build enriched prompt with real data
    briefing_str = json.dumps(state.briefing, default=str)[:4000]
    tool_data_str = json.dumps(tool_results, default=str)[:4000]

    user_prompt = (
        f"Policy question: {state.query}\n"
        f"Policy classification: {json.dumps(state.policy_params)}\n"
        f"User context: {json.dumps(state.user_context)}\n\n"
        f"Briefing packet (from Analyst Agent):\n{briefing_str}\n\n"
        f"REAL DATA from government APIs (FRED, BLS) and computed scenarios:\n{tool_data_str}\n\n"
        f"Use the actual numbers from this data in your analysis. Cite specific values."
    )

    # Step 3: LLM analysis
    report: SectorReport
    try:
        logger.info(f"Sector {sector}: calling LLM with {len(user_prompt)} char prompt...")
        raw = await llm_chat(
            system_prompt=SECTOR_PROMPTS[sector],
            user_prompt=user_prompt,
            json_mode=True,
            temperature=0.3,
            max_tokens=8000,
        )
        if raw:
            logger.info(f"Sector {sector}: LLM returned {len(raw)} chars")
            report = _parse_sector_report(sector, raw, tool_records)
            if not report.direct_effects:
                logger.warning(f"Sector {sector}: parsed report has 0 direct_effects, raw[:500]={raw[:500]}")
        else:
            logger.warning(f"Sector {sector}: LLM returned None (no API key configured?)")
            report = _error_report(sector, "LLM returned no response — check API key configuration")
    except Exception:
        logger.error(f"Sector {sector} LLM failed: {traceback.format_exc()}")
        report = _error_report(sector, f"LLM call failed: {traceback.format_exc()[:300]}")

    report.agent_mode = "single_shot"
    return report


# Phase descriptions for SSE events — maps LangGraph node names to human-readable labels
HOUSING_PHASES: dict[str, dict[str, str]] = {
    "phase_1_pathways":      {"phase": "1", "label": "Identifying transmission pathways",      "detail": "Reasoning about how policy connects to housing"},
    "phase_2_baseline":      {"phase": "2", "label": "Gathering housing market baseline",      "detail": "Pulling FRED, BLS, Census, HUD data"},
    "phase_3_magnitudes":    {"phase": "3", "label": "Estimating impact magnitudes",           "detail": "Running elasticity + scenario models"},
    "phase_4_distributional":{"phase": "4", "label": "Distributional & temporal analysis",     "detail": "Who wins, who loses, and when"},
    "phase_5_scorecard":     {"phase": "5", "label": "Building affordability scorecard",       "detail": "Final housing report with sub-market impacts"},
}

CONSUMER_PHASES: dict[str, dict[str, str]] = {
    "phase_1_shock":           {"phase": "1", "label": "Identifying price shock entry points", "detail": "Where does the cost shock enter the economy?"},
    "phase_2_passthrough":     {"phase": "2", "label": "Estimating pass-through rates",        "detail": "Pulling CPI, PPI data + market structure analysis"},
    "phase_3_geo_behavioral":  {"phase": "3", "label": "Geographic & behavioral analysis",     "detail": "Regional price impacts + substitution patterns"},
    "phase_4_purchasing_power":{"phase": "4", "label": "Net purchasing power calculation",     "detail": "Income gains vs cost increases per household type"},
    "phase_5_scorecard":       {"phase": "5", "label": "Building consumer impact scorecard",   "detail": "Final consumer report with household-level impacts"},
}


async def _run_langgraph_sector(
    sector: str,
    state: PipelineState,
    emit: EventCallback,
) -> SectorReport:
    """Run a LangGraph multi-phase sector agent (housing or consumer).

    Uses graph.astream() to emit real-time SSE events after each phase completes,
    so the frontend shows live progress.

    Falls back to single-shot if the LangGraph agent fails to import or errors out.
    """
    from backend.pipeline.langgraph_adapter import (
        briefing_dict_to_analyst_briefing,
        housing_report_to_sector_report,
        consumer_report_to_sector_report,
    )

    await emit({
        "type": "sector_agent_started",
        "agent": sector,
        "data": {
            "sector": sector,
            "agent": sector.title(),
            "agent_mode": "agentic",
        },
    })

    try:
        # Bridge pipeline briefing dict → AnalystBriefing Pydantic model
        analyst_briefing = briefing_dict_to_analyst_briefing(state.briefing)
        logger.info(f"Sector {sector}: ✅ AnalystBriefing bridge built successfully")

        policy_query = state.query
        if analyst_briefing.policy_spec:
            policy_query = f"{analyst_briefing.policy_spec.action}: {analyst_briefing.policy_spec.value}"

        # Build graph and initial state based on sector
        if sector == "housing":
            from backend.agents.housing.graph import build_housing_graph
            from backend.agents.housing.schemas import HousingState
            logger.info(f"Sector {sector}: ✅ LangGraph housing imports succeeded")

            graph = build_housing_graph()
            phase_map = HOUSING_PHASES
            convert_fn = housing_report_to_sector_report
            initial: dict = {
                "analyst_briefing": analyst_briefing,
                "policy_query": policy_query,
                "current_phase": 1,
                "phase_1_output": None,
                "phase_2_output": None,
                "phase_3_output": None,
                "phase_4_output": None,
                "phase_5_output": None,
                "tool_call_log": [],
            }

        elif sector == "consumer":
            from backend.agents.consumer.graph import build_consumer_graph
            from backend.agents.consumer.schemas import ConsumerState
            logger.info(f"Sector {sector}: ✅ LangGraph consumer imports succeeded")

            graph = build_consumer_graph()
            phase_map = CONSUMER_PHASES
            convert_fn = consumer_report_to_sector_report
            initial: dict = {
                "analyst_briefing": analyst_briefing,
                "policy_query": policy_query,
                "current_phase": 1,
                "phase_1_output": None,
                "phase_2_output": None,
                "phase_3_output": None,
                "phase_4_output": None,
                "phase_5_output": None,
                "tool_call_log": [],
            }
        else:
            return await _run_one_sector_single_shot(sector, state, emit)

        # --- Stream the graph with astream_events for real-time thinking feed ---
        logger.info(f"Sector {sector}: 🚀 STARTING LangGraph 5-phase agent (agentic mode)")

        async def _emit_thinking(step_type: str, content: str, **extra: Any) -> None:
            """Emit a thinking step to the frontend feed."""
            await emit({
                "type": "sector_agent_thinking",
                "agent": sector,
                "data": {
                    "agent": sector.title(),
                    "step_type": step_type,
                    "content": content,
                    **extra,
                },
            })

        await _emit_thinking("phase_start", "Starting 5-phase agentic pipeline", phase="0")

        final_state = {}
        current_phase = "1"
        seen_tool_ids: set[str] = set()

        try:
            async for event in graph.astream_events(initial, version="v2"):
                kind = event.get("event", "")
                name = event.get("name", "")
                run_id = event.get("run_id", "")

                # --- Phase node starts ---
                if kind == "on_chain_start" and name in phase_map:
                    phase_info = phase_map[name]
                    current_phase = phase_info["phase"]
                    logger.info(f"Sector {sector}: Phase {current_phase} starting — {phase_info['label']}")

                    await emit({
                        "type": "sector_agent_tool_call",
                        "agent": sector,
                        "data": {
                            "agent": sector.title(),
                            "tool": f"phase_{current_phase}",
                            "query": phase_info["label"],
                            "phase": current_phase,
                            "phase_detail": phase_info["detail"],
                        },
                    })
                    await _emit_thinking("phase_start", phase_info["detail"], phase=current_phase)

                # --- Phase node completes ---
                elif kind == "on_chain_end" and name in phase_map:
                    phase_info = phase_map[name]
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        final_state.update(output)
                    logger.info(f"Sector {sector}: Phase {phase_info['phase']} ✅ complete")
                    await _emit_thinking("phase_complete", f"Phase {phase_info['phase']} complete: {phase_info['label']}", phase=phase_info["phase"])

                # --- Tool invocation starts ---
                elif kind == "on_tool_start":
                    tool_input = event.get("data", {}).get("input", {})
                    tool_id = f"{run_id}:{name}"
                    if tool_id not in seen_tool_ids:
                        seen_tool_ids.add(tool_id)
                        # Format tool args for display
                        if isinstance(tool_input, dict):
                            args_str = ", ".join(f"{k}={v}" for k, v in list(tool_input.items())[:3])
                        else:
                            args_str = str(tool_input)[:100]
                        await _emit_thinking("tool_call", f"Calling {name}({args_str})", phase=current_phase, tool=name)

                # --- Tool invocation completes ---
                elif kind == "on_tool_end":
                    tool_output = event.get("data", {}).get("output", "")
                    output_str = str(tool_output)[:150] if tool_output else "no data"
                    await _emit_thinking("tool_result", f"{name} → {output_str}", phase=current_phase, tool=name)

                # --- LLM starts generating ---
                elif kind == "on_chat_model_start":
                    await _emit_thinking("reasoning", "Analyzing data and forming conclusions...", phase=current_phase)

                # --- LLM streaming tokens (first chunk = "thinking started") ---
                elif kind == "on_chat_model_stream":
                    # We don't stream every token (too noisy for SSE).
                    # But we capture the first ~200 chars of content for a thinking preview.
                    chunk_content = event.get("data", {})
                    if hasattr(chunk_content, "content") and chunk_content.content:
                        text = chunk_content.content if isinstance(chunk_content.content, str) else str(chunk_content.content)
                        # Only emit substantial chunks (not individual tokens)
                        if len(text) > 30:
                            await _emit_thinking("reasoning_chunk", text[:200], phase=current_phase)

        except Exception as stream_err:
            # astream_events failed — fall back to regular astream
            logger.warning(
                f"Sector {sector}: astream_events failed ({stream_err}), falling back to astream"
            )
            await _emit_thinking("reasoning", "Switching to batch processing mode...", phase=current_phase)

            async for chunk in graph.astream(initial):
                for node_name, node_output in chunk.items():
                    final_state.update(node_output)
                    phase_info = phase_map.get(node_name)
                    if phase_info:
                        current_phase = phase_info["phase"]
                        await emit({
                            "type": "sector_agent_tool_call",
                            "agent": sector,
                            "data": {
                                "agent": sector.title(),
                                "tool": f"phase_{current_phase}",
                                "query": phase_info["label"],
                                "phase": current_phase,
                                "phase_detail": phase_info["detail"],
                            },
                        })
                        await _emit_thinking("phase_complete", phase_info["label"], phase=current_phase)

        # Extract the final report from phase 5
        final_report = final_state.get("phase_5_output")
        if final_report is None:
            error_msg = "LangGraph produced no phase_5_output after all 5 phases"
            logger.error(f"Sector {sector}: ❌ {error_msg}")
            await emit({
                "type": "sector_agent_tool_call",
                "agent": sector,
                "data": {
                    "agent": sector.title(),
                    "tool": "langgraph_fallback",
                    "query": f"⚠️ FALLING BACK to single-shot: {error_msg}",
                },
            })
            fallback = await _run_one_sector_single_shot(sector, state, emit)
            fallback.agent_mode = "single_shot"
            return fallback

        all_tool_records = final_state.get("tool_call_log", [])
        logger.info(f"Sector {sector}: ✅ LangGraph complete with {len(all_tool_records)} tool calls")

        report = convert_fn(final_report, all_tool_records)
        logger.info(
            f"Sector {sector}: ✅ AGENTIC FLOW SUCCESS — "
            f"{len(report.direct_effects)} direct, "
            f"{len(report.second_order_effects)} second-order, "
            f"{len(all_tool_records)} tool calls"
        )
        return report

    except Exception:
        error_msg = traceback.format_exc()
        logger.error(
            f"Sector {sector}: ❌ LANGGRAPH AGENT FAILED — falling back to single-shot:\n"
            f"{error_msg}"
        )
        await emit({
            "type": "sector_agent_tool_call",
            "agent": sector,
            "data": {
                "agent": sector.title(),
                "tool": "langgraph_fallback",
                "query": f"⚠️ FALLING BACK to single-shot: {error_msg[:200]}",
            },
        })
        fallback = await _run_one_sector_single_shot(sector, state, emit)
        fallback.agent_mode = "single_shot"
        return fallback


# Sectors that have full LangGraph agents (Rudra's implementation)
LANGGRAPH_SECTORS = {"housing", "consumer"}


async def _emit_sector_complete(sector: str, report: SectorReport, emit: EventCallback) -> None:
    """Emit the sector_agent_complete SSE event with properly formatted report data."""
    report_dict = report.model_dump()
    for claim_list_key in ("direct_effects", "second_order_effects", "feedback_loops"):
        for claim_dict in report_dict.get(claim_list_key, []):
            if "confidence" in claim_dict:
                claim_dict["confidence"] = claim_dict["confidence"].upper()

    await emit({
        "type": "sector_agent_complete",
        "agent": sector,
        "data": {
            "agent": sector.title(),
            "report": report_dict,
            "sector": sector,
            "agent_mode": report.agent_mode,
            "direct_effects": len(report.direct_effects),
            "second_order_effects": len(report.second_order_effects),
            "feedback_loops": len(report.feedback_loops),
            "has_dissent": report.dissent is not None,
            "tool_calls": len(report.tool_calls_made),
        },
    })


async def run_sector_agents(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 2: Run all 4 sector agents in parallel.

    Housing and Consumer use Rudra's LangGraph multi-phase agents.
    Labor and Business use single-shot LLM analysis (fallback).
    """
    async def _run_sector(sector: str) -> SectorReport:
        if sector in LANGGRAPH_SECTORS:
            report = await _run_langgraph_sector(sector, state, emit)
        else:
            report = await _run_one_sector_single_shot(sector, state, emit)
        await _emit_sector_complete(sector, report, emit)
        return report

    tasks = [_run_sector(sector) for sector in SECTORS]
    reports = await asyncio.gather(*tasks, return_exceptions=True)

    state.sector_reports = []
    for sector, result in zip(SECTORS, reports):
        if isinstance(result, Exception):
            logger.error(f"Sector {sector} failed: {result}")
            error = _error_report(sector, f"Agent crashed: {str(result)[:300]}")
            error.agent_mode = "single_shot"
            state.sector_reports.append(error)
        else:
            state.sector_reports.append(result)

    return state

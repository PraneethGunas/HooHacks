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
# Fallback demo responses (when no LLM key is available)
# ---------------------------------------------------------------------------

def _fallback_report(sector: str, state: PipelineState) -> SectorReport:
    """Generate a minimal demo SectorReport without LLM."""
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


def _normalize_confidence(raw_value: str) -> ConfidenceLevel:
    """Map LLM confidence strings to our enum, handling creative LLM outputs."""
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

    def _to_list(val: Any) -> list[str]:
        if isinstance(val, list):
            return [str(v) for v in val]
        if isinstance(val, str) and val:
            return [val]
        return []

    def _parse_claim(c: dict) -> CausalClaim:
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

    return SectorReport(
        sector=sector,
        direct_effects=[_parse_claim(c) for c in data.get("direct_effects", [])],
        second_order_effects=[_parse_claim(c) for c in data.get("second_order_effects", [])],
        feedback_loops=[_parse_claim(c) for c in data.get("feedback_loops", [])],
        cross_sector_dependencies=data.get("cross_sector_dependencies", []),
        dissent=data.get("dissent"),
        tool_calls_made=tool_records or [],
    )


async def _run_one_sector(
    sector: str,
    state: PipelineState,
    emit: EventCallback,
) -> SectorReport:
    """Run a single sector agent: tool calls → LLM analysis."""
    await emit({
        "type": "sector_agent_started",
        "agent": sector,
        "data": {
            "sector": sector,
            "agent": sector.title(),
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
            report = _fallback_report(sector, state)
    except Exception:
        logger.error(f"Sector {sector} LLM failed: {traceback.format_exc()}")
        report = _fallback_report(sector, state)

    # Emit completion
    await emit({
        "type": "sector_agent_complete",
        "agent": sector,
        "data": {
            "agent": sector.title(),
            "report": report.model_dump(),
            "sector": sector,
            "direct_effects": len(report.direct_effects),
            "second_order_effects": len(report.second_order_effects),
            "feedback_loops": len(report.feedback_loops),
            "has_dissent": report.dissent is not None,
            "tool_calls": len(tool_records),
        },
    })

    return report


async def run_sector_agents(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 2: Run all 4 sector agents in parallel."""
    tasks = [
        _run_one_sector(sector, state, emit)
        for sector in SECTORS
    ]
    reports = await asyncio.gather(*tasks, return_exceptions=True)

    state.sector_reports = []
    for sector, result in zip(SECTORS, reports):
        if isinstance(result, Exception):
            logger.error(f"Sector {sector} failed: {result}")
            state.sector_reports.append(_fallback_report(sector, state))
        else:
            state.sector_reports.append(result)

    return state

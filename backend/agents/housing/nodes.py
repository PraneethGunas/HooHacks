"""Phase node implementations for the Housing & Cost of Living sector agent."""

from __future__ import annotations

import logging

from backend.agents._helpers import (
    _run_react_phase,
    _run_reasoning_phase,
    summarize_phase_output,
)
from backend.agents.housing.prompts import (
    HOUSING_IDENTITY_SHORT,
    phase_1_system_prompt,
    phase_2_system_prompt,
)
from backend.agents.housing.schemas import (
    DistributionalTemporalOutput,
    HousingBaselineOutput,
    HousingReport,
    MagnitudeEstimationOutput,
    PathwayIdentificationOutput,
)
from backend.agents.housing.tool_wrappers import (
    HOUSING_PHASE_2_TOOLS,
    HOUSING_PHASE_3_TOOLS,
    HOUSING_PHASE_4_TOOLS,
    HOUSING_PHASE_5_TOOLS,
)

logger = logging.getLogger(__name__)


async def housing_phase_1_pathways(state: dict) -> dict:
    """Phase 1: Transmission Pathway Identification — No tools, reasoning."""
    logger.info("=== HOUSING PHASE 1: Transmission Pathways ===")
    prompt = phase_1_system_prompt(state["analyst_briefing"])

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Identify how this policy connects to housing and cost of living.",
    )

    output = PathwayIdentificationOutput(**parsed)
    logger.info(
        f"Housing Phase 1 complete: {len(output.pathways)} pathways, "
        f"primary: {output.primary_pathways}"
    )

    return {
        "current_phase": 2,
        "phase_1_output": output,
    }


async def housing_phase_2_baseline(state: dict) -> dict:
    """Phase 2: Housing Market Baseline — ReAct with FRED, BLS, Census, BEA, HUD."""
    logger.info("=== HOUSING PHASE 2: Housing Market Baseline ===")
    prompt = phase_2_system_prompt(state["analyst_briefing"], state["phase_1_output"])

    parsed, tool_records = await _run_react_phase(
        system_prompt=prompt,
        user_message="Pull housing market baseline data for the affected geography.",
        tools=HOUSING_PHASE_2_TOOLS,
        phase_num=2,
        state=state,
        recursion_limit=50,
    )

    output = HousingBaselineOutput(**parsed)
    logger.info(
        f"Housing Phase 2 complete: {len(output.supply_metrics)} supply, "
        f"{len(output.demand_metrics)} demand, {len(output.price_metrics)} price metrics, "
        f"{len(output.sub_markets)} sub-markets"
    )

    phase_2_summary = await summarize_phase_output(
        "Housing Baseline (Phase 2)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 3,
        "phase_2_output": output,
        "phase_2_summary": phase_2_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def housing_phase_3_magnitudes(state: dict) -> dict:
    """Phase 3: Magnitude Estimation — ReAct with code_execute + data tools.

    Uses short system prompt + detailed user message (Gemini needs this pattern
    for reliable tool calling with analytical context).
    """
    logger.info("=== HOUSING PHASE 3: Magnitude Estimation ===")

    policy_desc = ""
    briefing = state["analyst_briefing"]
    if briefing.policy_spec:
        policy_desc = f"{briefing.policy_spec.action}: {briefing.policy_spec.value}"

    pathways_summary = "\n".join(
        f"- {p.pathway_id} {p.name}: relevance={p.relevance}, direction={p.direction}"
        for p in state["phase_1_output"].pathways
        if p.relevance in ("HIGH", "MEDIUM")
    )

    baseline_ctx = state.get("phase_2_summary", "No baseline summary available.")

    schema = MagnitudeEstimationOutput.model_json_schema()

    user_msg = f"""Compute housing impact magnitudes for this policy.

Policy: {policy_desc}

Relevant pathways:
{pathways_summary}

Housing baseline:
{baseline_ctx}

KEY ELASTICITIES — use these in your calculations:
- Rent elasticity w.r.t. income: 0.3 (loose markets) to 0.7 (tight markets)
- Construction cost pass-through to rent: 1% cost increase → 0.3-0.5% rent increase (long-run)
- Operating cost pass-through to rent: 50-80% within 12-18 months
- Mortgage rate sensitivity: 1pp rate increase → ~10% purchasing power reduction

For each HIGH/MEDIUM pathway, use code_execute to compute low/central/high estimates.
Then compute: NOMINAL wage change vs HOUSING COST change = NET REAL INCOME change.

Produce JSON matching this schema:
{schema}"""

    parsed, tool_records = await _run_react_phase(
        system_prompt=HOUSING_IDENTITY_SHORT,
        user_message=user_msg,
        tools=HOUSING_PHASE_3_TOOLS,
        phase_num=3,
        state=state,
        recursion_limit=30,
    )

    output = MagnitudeEstimationOutput(**parsed)
    logger.info(f"Housing Phase 3 complete: {len(output.estimates)} estimates")

    phase_3_summary = await summarize_phase_output(
        "Magnitude Estimates (Phase 3)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 4,
        "phase_3_output": output,
        "phase_3_summary": phase_3_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def housing_phase_4_distributional(state: dict) -> dict:
    """Phase 4: Distributional + Temporal Analysis — ReAct with code_execute."""
    logger.info("=== HOUSING PHASE 4: Distributional & Temporal ===")

    policy_desc = ""
    briefing = state["analyst_briefing"]
    if briefing.policy_spec:
        policy_desc = f"{briefing.policy_spec.action}: {briefing.policy_spec.value}"

    sub_markets = ", ".join(
        sm.name for sm in state["phase_2_output"].sub_markets
    ) if state["phase_2_output"].sub_markets else "national"

    estimates_ctx = state.get("phase_3_summary", "No magnitude estimates available.")
    baseline_ctx = state.get("phase_2_summary", "")

    schema = DistributionalTemporalOutput.model_json_schema()

    user_msg = f"""Compute distributional and temporal housing impacts.

Policy: {policy_desc}
Sub-markets: {sub_markets}

Magnitude estimates from Phase 3:
{estimates_ctx}

Baseline context:
{baseline_ctx}

Use code_execute to compute:

1. BY INCOME (3 tiers):
   - $35K/year: monthly housing budget = income/12 * housing_share. Rent-to-income before/after. Crosses 30% burden?
   - $55K/year: same
   - $85K/year: same

2. BY TENURE: Renters (rent pass-through) vs Owners (mortgage, equity)

3. BY GEOGRAPHY: Impact per sub-market based on tightness

4. TEMPORAL (4 horizons):
   - 0-6mo: demand pressure, fixed supply
   - 6-18mo: lease renewals, price adjustment
   - 18-36mo: construction costs adjust
   - 3-5yr+: supply equilibrium

Produce JSON matching this schema:
{schema}"""

    parsed, tool_records = await _run_react_phase(
        system_prompt=HOUSING_IDENTITY_SHORT,
        user_message=user_msg,
        tools=HOUSING_PHASE_4_TOOLS,
        phase_num=4,
        state=state,
        recursion_limit=30,
    )

    output = DistributionalTemporalOutput(**parsed)
    logger.info(
        f"Housing Phase 4 complete: {len(output.by_income)} income tiers, "
        f"{len(output.temporal_sequence)} temporal effects"
    )

    phase_4_summary = await summarize_phase_output(
        "Distributional & Temporal (Phase 4)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 5,
        "phase_4_output": output,
        "phase_4_summary": phase_4_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def housing_phase_5_scorecard(state: dict) -> dict:
    """Phase 5: Affordability Scorecard + Final Report — ReAct with code_execute."""
    logger.info("=== HOUSING PHASE 5: Affordability Scorecard ===")

    policy_desc = ""
    briefing = state["analyst_briefing"]
    if briefing.policy_spec:
        policy_desc = f"{briefing.policy_spec.action}: {briefing.policy_spec.value}"

    baseline_ctx = state.get("phase_2_summary", "")
    estimates_ctx = state.get("phase_3_summary", "")
    distributional_ctx = state.get("phase_4_summary", "")

    schema = HousingReport.model_json_schema()

    user_msg = f"""Produce the final Housing Affordability Scorecard and Report.

Policy: {policy_desc}

Housing Baseline:
{baseline_ctx}

Magnitude Estimates:
{estimates_ctx}

Distributional & Temporal:
{distributional_ctx}

Use code_execute to compute the AFFORDABILITY SCORECARD for each sub-market:
- Current: median rent, home price, mortgage payment (30yr at current rate), income, rent-to-income %, cost burden rate
- Policy impact (12-18mo): rent change $/mo, home price change %, mortgage payment change
- Net affordability: improving/worsening/mixed
- Dollar impact at $35K, $55K, $85K income levels

Also include CausalClaims:
- direct_effects: 2-3 primary housing impacts (rent changes, price changes) with mechanism and confidence
- second_order_effects: 1-2 supply/migration responses
- cross_sector_dependencies: 2-3 signals for other sectors (labor, consumer, business)

Produce JSON matching this schema:
{schema}"""

    parsed, tool_records = await _run_react_phase(
        system_prompt=HOUSING_IDENTITY_SHORT,
        user_message=user_msg,
        tools=HOUSING_PHASE_5_TOOLS,
        phase_num=5,
        state=state,
        recursion_limit=30,
    )

    parsed.setdefault("sector", "housing")
    report = HousingReport(**parsed)
    report.pathway_analysis = state["phase_1_output"]
    report.housing_baseline = state["phase_2_output"]
    report.magnitude_estimates = state["phase_3_output"]
    report.distributional_temporal = state["phase_4_output"]

    logger.info("Housing Phase 5 complete: Housing report produced")

    return {
        "current_phase": 5,
        "phase_5_output": report,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }

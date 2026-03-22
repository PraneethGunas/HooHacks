"""Phase node implementations for the Consumer & Prices sector agent."""

from __future__ import annotations

import logging

from backend.agents._helpers import (
    _run_react_phase,
    _run_reasoning_phase,
    summarize_phase_output,
)
from backend.agents.consumer.prompts import (
    CONSUMER_IDENTITY_SHORT,
    phase_1_system_prompt,
    phase_2_system_prompt,
    phase_3_system_prompt,
    phase_4_system_prompt,
    phase_5_system_prompt,
)
from backend.agents.consumer.schemas import (
    ConsumerReport,
    GeoBehavioralOutput,
    PassThroughBaselineOutput,
    PriceShockOutput,
    PurchasingPowerOutput,
)
from backend.agents.consumer.tool_wrappers import (
    CONSUMER_PHASE_2_TOOLS,
    CONSUMER_PHASE_3_TOOLS,
    CONSUMER_PHASE_4_TOOLS,
    CONSUMER_PHASE_5_TOOLS,
)

logger = logging.getLogger(__name__)


async def consumer_phase_1_shock(state: dict) -> dict:
    """Phase 1: Price Shock Entry Point — No tools, reasoning."""
    logger.info("=== CONSUMER PHASE 1: Price Shock Entry Point ===")
    prompt = phase_1_system_prompt(state["analyst_briefing"])

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Identify where this policy enters the price system and which categories are affected.",
    )

    output = PriceShockOutput(**parsed)
    logger.info(
        f"Consumer Phase 1 complete: {len(output.entry_points)} entry points, "
        f"primary: {output.primary_entry}"
    )

    return {
        "current_phase": 2,
        "phase_1_output": output,
    }


async def consumer_phase_2_passthrough(state: dict) -> dict:
    """Phase 2: Pass-Through + Baseline — ReAct with BLS, FRED, Census, BEA, etc."""
    logger.info("=== CONSUMER PHASE 2: Pass-Through + Baseline ===")
    prompt = phase_2_system_prompt(state["analyst_briefing"], state["phase_1_output"])

    parsed, tool_records = await _run_react_phase(
        system_prompt=prompt,
        user_message="Pull CPI/PPI data, estimate pass-through rates, and gather income/spending baselines.",
        tools=CONSUMER_PHASE_2_TOOLS,
        phase_num=2,
        state=state,
        recursion_limit=50,
    )

    output = PassThroughBaselineOutput(**parsed)
    logger.info(
        f"Consumer Phase 2 complete: {len(output.pass_through_estimates)} pass-through estimates, "
        f"{len(output.category_baselines)} category baselines"
    )

    phase_2_summary = await summarize_phase_output(
        "Pass-Through & Baseline (Phase 2)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 3,
        "phase_2_output": output,
        "phase_2_summary": phase_2_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def consumer_phase_3_geo_behavioral(state: dict) -> dict:
    """Phase 3: Geographic + Behavioral — ReAct with code_execute + BEA + Census."""
    logger.info("=== CONSUMER PHASE 3: Geographic + Behavioral ===")

    user_msg = phase_3_system_prompt(
        state["phase_1_output"],
        state["phase_2_output"],
        phase_2_summary=state.get("phase_2_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=CONSUMER_IDENTITY_SHORT,
        user_message=user_msg,
        tools=CONSUMER_PHASE_3_TOOLS,
        phase_num=3,
        state=state,
        recursion_limit=30,
    )

    output = GeoBehavioralOutput(**parsed)
    logger.info(f"Consumer Phase 3 complete: {len(output.regional_impacts)} regions")

    phase_3_summary = await summarize_phase_output(
        "Geographic & Behavioral (Phase 3)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 4,
        "phase_3_output": output,
        "phase_3_summary": phase_3_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def consumer_phase_4_purchasing_power(state: dict) -> dict:
    """Phase 4: Net Purchasing Power — ReAct with code_execute."""
    logger.info("=== CONSUMER PHASE 4: Net Purchasing Power ===")

    user_msg = phase_4_system_prompt(
        state["analyst_briefing"],
        state["phase_1_output"],
        phase_2_summary=state.get("phase_2_summary"),
        phase_3_summary=state.get("phase_3_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=CONSUMER_IDENTITY_SHORT,
        user_message=user_msg,
        tools=CONSUMER_PHASE_4_TOOLS,
        phase_num=4,
        state=state,
        recursion_limit=30,
    )

    output = PurchasingPowerOutput(**parsed)
    logger.info(
        f"Consumer Phase 4 complete: {len(output.household_profiles)} profiles, "
        f"{len(output.temporal_effects)} temporal effects"
    )

    phase_4_summary = await summarize_phase_output(
        "Purchasing Power (Phase 4)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 5,
        "phase_4_output": output,
        "phase_4_summary": phase_4_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def consumer_phase_5_scorecard(state: dict) -> dict:
    """Phase 5: Consumer Impact Scorecard + Final Report — ReAct with code_execute."""
    logger.info("=== CONSUMER PHASE 5: Consumer Impact Scorecard ===")

    user_msg = phase_5_system_prompt(
        state["analyst_briefing"],
        phase_2_summary=state.get("phase_2_summary"),
        phase_3_summary=state.get("phase_3_summary"),
        phase_4_summary=state.get("phase_4_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=CONSUMER_IDENTITY_SHORT,
        user_message=user_msg,
        tools=CONSUMER_PHASE_5_TOOLS,
        phase_num=5,
        state=state,
        recursion_limit=30,
    )

    parsed.setdefault("sector", "consumer")
    report = ConsumerReport(**parsed)
    report.price_shock_analysis = state["phase_1_output"]
    report.pass_through_baseline = state["phase_2_output"]
    report.geo_behavioral = state["phase_3_output"]
    report.purchasing_power = state["phase_4_output"]

    logger.info("Consumer Phase 5 complete: Consumer report produced")

    return {
        "current_phase": 5,
        "phase_5_output": report,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }

"""Phase node implementations for the Synthesis & Impact Dashboard agent."""

from __future__ import annotations

import logging

from backend.agents._helpers import (
    _run_react_phase,
    _run_reasoning_phase,
    summarize_phase_output,
)
from backend.agents.synthesis.prompts import (
    SYNTHESIS_IDENTITY_SHORT,
    phase_1_system_prompt,
    phase_2_system_prompt,
    phase_3_system_prompt,
    phase_4_system_prompt,
    phase_5_system_prompt,
)
from backend.agents.synthesis.schemas import (
    ConsistencyAuditOutput,
    NarrativeOutput,
    NetImpactOutput,
    SynthesisReport,
    WinnersLosersOutput,
)
from backend.agents.synthesis.tool_wrappers import (
    SYNTHESIS_PHASE_2_TOOLS,
    SYNTHESIS_PHASE_3_TOOLS,
    SYNTHESIS_PHASE_5_TOOLS,
)

logger = logging.getLogger(__name__)


async def synthesis_phase_1_audit(state: dict) -> dict:
    """Phase 1: Input Validation + Consistency Audit — reasoning only."""
    logger.info("=== SYNTHESIS PHASE 1: Consistency Audit ===")
    prompt = phase_1_system_prompt(
        state["analyst_briefing"],
        state.get("housing_report"),
        state.get("consumer_report"),
    )

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Audit all upstream agent outputs for completeness and cross-agent consistency.",
    )

    output = ConsistencyAuditOutput(**parsed)
    logger.info(
        f"Synthesis Phase 1 complete: {len(output.input_inventory)} agents inventoried, "
        f"{len(output.inconsistencies)} inconsistencies found"
    )

    phase_1_summary = await summarize_phase_output(
        "Consistency Audit (Phase 1)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 2,
        "phase_1_output": output,
        "phase_1_summary": phase_1_summary,
    }


async def synthesis_phase_2_impact(state: dict) -> dict:
    """Phase 2: Net Household Impact Computation — code_execute."""
    logger.info("=== SYNTHESIS PHASE 2: Net Impact Computation ===")

    user_msg = phase_2_system_prompt(
        state["analyst_briefing"],
        state.get("housing_report"),
        state.get("consumer_report"),
        phase_1_summary=state.get("phase_1_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=SYNTHESIS_IDENTITY_SHORT,
        user_message=user_msg,
        tools=SYNTHESIS_PHASE_2_TOOLS,
        phase_num=2,
        state=state,
        recursion_limit=30,
    )

    output = NetImpactOutput(**parsed)
    logger.info(f"Synthesis Phase 2 complete: {len(output.household_impacts)} profiles computed")

    phase_2_summary = await summarize_phase_output(
        "Net Impact (Phase 2)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 3,
        "phase_2_output": output,
        "phase_2_summary": phase_2_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def synthesis_phase_3_winners(state: dict) -> dict:
    """Phase 3: Winners/Losers + Confidence — code_execute."""
    logger.info("=== SYNTHESIS PHASE 3: Winners & Losers ===")

    user_msg = phase_3_system_prompt(
        phase_2_summary=state.get("phase_2_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=SYNTHESIS_IDENTITY_SHORT,
        user_message=user_msg,
        tools=SYNTHESIS_PHASE_3_TOOLS,
        phase_num=3,
        state=state,
        recursion_limit=20,
    )

    output = WinnersLosersOutput(**parsed)
    logger.info(
        f"Synthesis Phase 3 complete: {len(output.winners)} winners, "
        f"{len(output.losers)} losers, {len(output.mixed)} mixed"
    )

    phase_3_summary = await summarize_phase_output(
        "Winners & Losers (Phase 3)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 4,
        "phase_3_output": output,
        "phase_3_summary": phase_3_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def synthesis_phase_4_narrative(state: dict) -> dict:
    """Phase 4: Timeline + Narrative — reasoning only."""
    logger.info("=== SYNTHESIS PHASE 4: Narrative ===")

    prompt = phase_4_system_prompt(
        state["analyst_briefing"],
        phase_1_summary=state.get("phase_1_summary"),
        phase_2_summary=state.get("phase_2_summary"),
        phase_3_summary=state.get("phase_3_summary"),
    )

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Produce the plain-language narrative summary and unified timeline.",
    )

    output = NarrativeOutput(**parsed)
    logger.info(f"Synthesis Phase 4 complete: {len(output.key_findings)} key findings")

    phase_4_summary = await summarize_phase_output(
        "Narrative (Phase 4)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 5,
        "phase_4_output": output,
        "phase_4_summary": phase_4_summary,
    }


async def synthesis_phase_5_payload(state: dict) -> dict:
    """Phase 5: Analytics Payload — code_execute for final structuring."""
    logger.info("=== SYNTHESIS PHASE 5: Analytics Payload ===")

    user_msg = phase_5_system_prompt(
        state["analyst_briefing"],
        phase_1_summary=state.get("phase_1_summary"),
        phase_2_summary=state.get("phase_2_summary"),
        phase_3_summary=state.get("phase_3_summary"),
        phase_4_summary=state.get("phase_4_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=SYNTHESIS_IDENTITY_SHORT,
        user_message=user_msg,
        tools=SYNTHESIS_PHASE_5_TOOLS,
        phase_num=5,
        state=state,
        recursion_limit=30,
    )

    report = SynthesisReport(**parsed)

    # Inject phase outputs
    report.consistency_audit = state.get("phase_1_output")
    report.narrative = state.get("phase_4_output")
    if state.get("phase_3_output"):
        report.winners_losers = state["phase_3_output"]
    if state.get("phase_2_output"):
        report.household_impacts = state["phase_2_output"].household_impacts
        report.waterfall = state["phase_2_output"].waterfall

    logger.info("Synthesis Phase 5 complete: Final report produced")

    return {
        "current_phase": 5,
        "phase_5_output": report,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }

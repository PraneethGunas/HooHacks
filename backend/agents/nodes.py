"""Phase node implementations for the analyst agent.

Each function takes the graph state dict and returns a partial state update.
- Tool phases (1, 2, 4): use create_react_agent for ReAct loop
- No-tool phases (3, 5): single LLM invocation
"""

from __future__ import annotations

import json
import logging

from backend.agents._helpers import _run_react_phase, _run_reasoning_phase
from backend.agents.prompts import (
    phase_1_system_prompt,
    phase_2_system_prompt,
    phase_3_system_prompt,
    phase_4_system_prompt,
    phase_5_system_prompt,
)
from backend.agents.schemas import (
    AnalystBriefing,
    BaselineOutput,
    EvidenceOutput,
    PolicySpec,
    TransmissionMapOutput,
)
from backend.agents.tool_wrappers import PHASE_1_TOOLS, PHASE_2_TOOLS, PHASE_4_TOOLS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase Nodes
# ---------------------------------------------------------------------------


async def phase_1_policy_spec(state: dict) -> dict:
    """Phase 1: Policy Specification — ReAct with web search, doc fetch, FRED."""
    logger.info("=== PHASE 1: Policy Specification ===")
    policy_query = state["policy_query"]
    prompt = phase_1_system_prompt(policy_query)

    parsed, tool_records = await _run_react_phase(
        system_prompt=prompt,
        user_message=f"Analyze this policy proposal: {policy_query}",
        tools=PHASE_1_TOOLS,
        phase_num=1,
        state=state,
    )

    policy_spec = PolicySpec(**parsed)
    logger.info(f"Phase 1 complete: {policy_spec.action} — {policy_spec.value}")

    return {
        "current_phase": 2,
        "phase_1_output": policy_spec,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def phase_2_baseline(state: dict) -> dict:
    """Phase 2: Baseline & Counterfactual — ReAct with FRED + BLS."""
    logger.info("=== PHASE 2: Baseline & Counterfactual ===")
    prompt = phase_2_system_prompt(state["policy_query"], state["phase_1_output"])

    parsed, tool_records = await _run_react_phase(
        system_prompt=prompt,
        user_message="Construct the baseline and counterfactual for this policy.",
        tools=PHASE_2_TOOLS,
        phase_num=2,
        state=state,
    )

    baseline = BaselineOutput(**parsed)
    logger.info(f"Phase 2 complete: {len(baseline.key_metrics)} metrics gathered")

    return {
        "current_phase": 3,
        "phase_2_output": baseline,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def phase_3_transmission(state: dict) -> dict:
    """Phase 3: Transmission Channel Mapping — No tools, pure reasoning."""
    logger.info("=== PHASE 3: Transmission Channel Mapping ===")
    prompt = phase_3_system_prompt(
        state["policy_query"], state["phase_1_output"], state["phase_2_output"]
    )

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Map all transmission channels for this policy based on the data gathered.",
    )

    transmission_map = TransmissionMapOutput(**parsed)
    logger.info(f"Phase 3 complete: {len(transmission_map.channels)} channels identified")

    return {
        "current_phase": 4,
        "phase_3_output": transmission_map,
    }


async def phase_4_evidence(state: dict) -> dict:
    """Phase 4: Evidence Gathering — ReAct with academic search + CBO + news."""
    logger.info("=== PHASE 4: Evidence Gathering ===")
    prompt = phase_4_system_prompt(
        state["policy_query"],
        state["phase_1_output"],
        state["phase_2_output"],
        state["phase_3_output"],
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=prompt,
        user_message="Gather empirical evidence for each transmission channel.",
        tools=PHASE_4_TOOLS,
        phase_num=4,
        state=state,
        recursion_limit=60,  # Phase 4 makes the most tool calls
    )

    evidence = EvidenceOutput(**parsed)
    logger.info(
        f"Phase 4 complete: evidence for {len(evidence.evidence_by_channel)} channels"
    )

    return {
        "current_phase": 5,
        "phase_4_output": evidence,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def phase_5_synthesis(state: dict) -> dict:
    """Phase 5: Synthesis & Briefing — No tools, produces final AnalystBriefing."""
    logger.info("=== PHASE 5: Synthesis & Briefing ===")
    prompt = phase_5_system_prompt(
        state["policy_query"],
        state["phase_1_output"],
        state["phase_2_output"],
        state["phase_3_output"],
        state["phase_4_output"],
    )

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Produce the final analyst briefing.",
    )

    # Inject prior phase data into the briefing if the LLM didn't include it
    if "policy_spec" not in parsed or parsed["policy_spec"] is None:
        parsed["policy_spec"] = state["phase_1_output"].model_dump()
    if "baseline" not in parsed or parsed["baseline"] is None:
        parsed["baseline"] = state["phase_2_output"].model_dump()
    if "transmission_channels" not in parsed or not parsed["transmission_channels"]:
        parsed["transmission_channels"] = [
            c.model_dump() for c in state["phase_3_output"].channels
        ]
    if "evidence" not in parsed or parsed["evidence"] is None:
        parsed["evidence"] = state["phase_4_output"].model_dump()

    briefing = AnalystBriefing(**parsed)
    logger.info("Phase 5 complete: Analyst briefing produced")

    return {
        "current_phase": 5,
        "phase_5_output": briefing,
    }

"""Integration tests for the Consumer & Prices sector agent."""

import pytest
from backend.agents.run import run_analyst_agent
from backend.agents.consumer.run import run_consumer_agent
from backend.agents.consumer.schemas import ConsumerReport


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_consumer_agent_phases():
    """Run consumer agent and verify all 5 phases produce output."""
    analyst = await run_analyst_agent("Raise the federal minimum wage to $15/hr")
    briefing = analyst["phase_5_output"]
    assert briefing is not None

    state = await run_consumer_agent(briefing, "Raise the federal minimum wage to $15/hr")

    # Phase 1: Price shock entry
    p1 = state.get("phase_1_output")
    assert p1 is not None, "Phase 1 missing"
    assert len(p1.entry_points) >= 1
    assert p1.primary_entry
    print(f"\nPhase 1: {len(p1.entry_points)} entry points, primary={p1.primary_entry}")

    # Phase 2: Pass-through + baseline
    p2 = state.get("phase_2_output")
    assert p2 is not None, "Phase 2 missing"
    print(f"Phase 2: {len(p2.pass_through_estimates)} pass-through, {len(p2.category_baselines)} baselines")

    # Phase 2 summary
    assert state.get("phase_2_summary"), "Phase 2 summary missing"

    # Phase 3: Geographic + behavioral
    p3 = state.get("phase_3_output")
    assert p3 is not None, "Phase 3 missing"
    print(f"Phase 3: {len(p3.regional_impacts)} regions")

    # Phase 4: Purchasing power
    p4 = state.get("phase_4_output")
    assert p4 is not None, "Phase 4 missing"
    print(f"Phase 4: {len(p4.household_profiles)} profiles, {len(p4.temporal_effects)} temporal")

    # Phase 5: Final report
    p5 = state.get("phase_5_output")
    assert p5 is not None, "Phase 5 missing"
    assert isinstance(p5, ConsumerReport)
    assert p5.sector == "consumer"
    print(f"Phase 5: sector={p5.sector}, direct_effects={len(p5.direct_effects)}")

    tools = state.get("tool_call_log", [])
    assert len(tools) > 0
    print(f"Total tool calls: {len(tools)}")

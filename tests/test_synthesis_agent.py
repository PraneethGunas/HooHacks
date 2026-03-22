"""Integration tests for the Synthesis & Impact Dashboard agent."""

import pytest
from backend.agents.run import run_analyst_agent
from backend.agents.housing.run import run_housing_agent
from backend.agents.consumer.run import run_consumer_agent
from backend.agents.synthesis.run import run_synthesis_agent
from backend.agents.synthesis.schemas import SynthesisReport


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_synthesis_agent_phases():
    """Run synthesis agent with real upstream outputs and verify all phases."""
    # Stage 1: Analyst
    analyst = await run_analyst_agent("Raise the federal minimum wage to $15/hr")
    briefing = analyst["phase_5_output"]
    assert briefing is not None

    # Stage 2: Housing + Consumer (sequential here for test reliability)
    housing_state = await run_housing_agent(briefing, "Raise the federal minimum wage to $15/hr")
    consumer_state = await run_consumer_agent(briefing, "Raise the federal minimum wage to $15/hr")

    housing_report = housing_state.get("phase_5_output")
    consumer_report = consumer_state.get("phase_5_output")

    # Stage 3: Synthesis
    state = await run_synthesis_agent(
        analyst_briefing=briefing,
        housing_report=housing_report,
        consumer_report=consumer_report,
        policy_query="Raise the federal minimum wage to $15/hr",
    )

    # Phase 1: Consistency audit
    p1 = state.get("phase_1_output")
    assert p1 is not None, "Phase 1 missing"
    assert len(p1.input_inventory) >= 2
    print(f"\nPhase 1: {len(p1.input_inventory)} agents, {len(p1.inconsistencies)} inconsistencies")

    # Phase 2: Net impact
    p2 = state.get("phase_2_output")
    assert p2 is not None, "Phase 2 missing"
    print(f"Phase 2: {len(p2.household_impacts)} household profiles")

    # Phase 3: Winners/losers
    p3 = state.get("phase_3_output")
    assert p3 is not None, "Phase 3 missing"
    print(f"Phase 3: {len(p3.winners)} winners, {len(p3.losers)} losers, {len(p3.mixed)} mixed")

    # Phase 4: Narrative
    p4 = state.get("phase_4_output")
    assert p4 is not None, "Phase 4 missing"
    assert p4.executive_summary
    assert len(p4.key_findings) >= 2
    print(f"Phase 4: {len(p4.key_findings)} findings, timeline={len(p4.timeline)} horizons")

    # Phase 5: Final report
    p5 = state.get("phase_5_output")
    assert p5 is not None, "Phase 5 missing"
    assert isinstance(p5, SynthesisReport)
    assert p5.policy_title or p5.policy_one_liner
    print(f"Phase 5: {p5.policy_title}")
    print(f"  Confidence: {p5.overall_confidence}")
    if p5.narrative:
        print(f"  Bottom line: {p5.narrative.bottom_line}")


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_synthesis_handles_missing_agents():
    """Synthesis should work even when some sector agents are missing."""
    analyst = await run_analyst_agent("Impose a 25% tariff on all Chinese imports")
    briefing = analyst["phase_5_output"]
    assert briefing is not None

    # Run synthesis with NO sector agents (only analyst briefing)
    state = await run_synthesis_agent(
        analyst_briefing=briefing,
        housing_report=None,
        consumer_report=None,
        policy_query="Impose a 25% tariff on all Chinese imports",
    )

    # Should still produce a report, noting missing inputs
    p1 = state.get("phase_1_output")
    assert p1 is not None
    assert len(p1.missing_inputs) >= 1 or any(
        inv.status == "MISSING" for inv in p1.input_inventory
    )
    print(f"\nMissing inputs flagged: {p1.missing_inputs}")

    p5 = state.get("phase_5_output")
    assert p5 is not None
    print(f"Report produced despite missing agents: {p5.policy_title}")

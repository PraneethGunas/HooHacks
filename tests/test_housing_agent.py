"""Integration tests for the Housing & Cost of Living sector agent."""

import pytest
from backend.agents.run import run_analyst_agent
from backend.agents.housing.run import run_housing_agent
from backend.agents.housing.schemas import HousingReport


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_housing_agent_phases():
    """Run housing agent and verify all 5 phases produce output."""
    # First get analyst briefing
    analyst = await run_analyst_agent("Raise the federal minimum wage to $15/hr")
    briefing = analyst["phase_5_output"]
    assert briefing is not None

    # Run housing agent
    state = await run_housing_agent(briefing, "Raise the federal minimum wage to $15/hr")

    # Phase 1: Transmission pathways
    p1 = state.get("phase_1_output")
    assert p1 is not None, "Phase 1 missing"
    assert len(p1.pathways) >= 3, f"Expected >=3 pathways, got {len(p1.pathways)}"
    assert len(p1.primary_pathways) >= 1
    print(f"\nPhase 1: {len(p1.pathways)} pathways, primary={p1.primary_pathways}")

    # Phase 2: Housing baseline
    p2 = state.get("phase_2_output")
    assert p2 is not None, "Phase 2 missing"
    total_metrics = len(p2.supply_metrics) + len(p2.demand_metrics) + len(p2.price_metrics)
    assert total_metrics >= 3, f"Expected >=3 total metrics, got {total_metrics}"
    print(f"Phase 2: {total_metrics} metrics, {len(p2.sub_markets)} sub-markets")

    # Phase 2 summary exists
    assert state.get("phase_2_summary"), "Phase 2 summary missing"

    # Phase 3: Magnitude estimates
    p3 = state.get("phase_3_output")
    assert p3 is not None, "Phase 3 missing"
    print(f"Phase 3: {len(p3.estimates)} magnitude estimates")

    # Phase 4: Distributional
    p4 = state.get("phase_4_output")
    assert p4 is not None, "Phase 4 missing"
    print(f"Phase 4: {len(p4.by_income)} income tiers, {len(p4.temporal_sequence)} temporal")

    # Phase 5: Final report
    p5 = state.get("phase_5_output")
    assert p5 is not None, "Phase 5 missing"
    assert isinstance(p5, HousingReport)
    assert p5.sector == "housing"
    print(f"Phase 5: sector={p5.sector}, direct_effects={len(p5.direct_effects)}")

    # Audit trail
    tools = state.get("tool_call_log", [])
    assert len(tools) > 0, "No tool calls recorded"
    print(f"Total tool calls: {len(tools)}")

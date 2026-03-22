"""CLI entry point for the Housing & Cost of Living sector agent."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from backend.agents.housing.graph import build_housing_graph
from backend.agents.housing.schemas import HousingState
from backend.agents.schemas import AnalystBriefing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def run_housing_agent(
    analyst_briefing: AnalystBriefing,
    policy_query: str = "",
) -> dict:
    """Run the full 5-phase housing agent and return the final state."""
    graph = build_housing_graph()

    query = policy_query
    if not query and analyst_briefing.policy_spec:
        query = f"{analyst_briefing.policy_spec.action}: {analyst_briefing.policy_spec.value}"

    initial_state: HousingState = {
        "analyst_briefing": analyst_briefing,
        "policy_query": query,
        "current_phase": 1,
        "phase_1_output": None,
        "phase_2_output": None,
        "phase_3_output": None,
        "phase_4_output": None,
        "phase_5_output": None,
        "tool_call_log": [],
    }

    final_state = await graph.ainvoke(initial_state)

    # Print summary
    report = final_state.get("phase_5_output")
    if report and report.affordability_scorecard:
        sc = report.affordability_scorecard
        print("\n" + "=" * 60)
        print("HOUSING AFFORDABILITY SCORECARD")
        print("=" * 60)
        for sm in sc.sub_markets:
            print(f"\n--- {sm.region_name} ---")
            print(f"  Current rent: {sm.current_median_rent}")
            print(f"  Current home price: {sm.current_median_home_price}")
            print(f"  Rent-to-income: {sm.current_rent_to_income}")
            print(f"  Policy rent change: {sm.rent_change}")
            print(f"  Net affordability: {sm.net_affordability_shift}")
            print(f"  Impact @$35K: {sm.impact_at_35k}")
            print(f"  Impact @$55K: {sm.impact_at_55k}")
            print(f"  Impact @$85K: {sm.impact_at_85k}")
        print(f"\nTool calls: {len(final_state.get('tool_call_log', []))}")
    elif report:
        print("\nHousing report produced but no affordability scorecard.")
        print(f"Direct effects: {len(report.direct_effects)}")
        print(f"Second order: {len(report.second_order_effects)}")
    else:
        print("\nHousing agent did not produce a final report. Check logs.")

    return final_state


async def _run_full_pipeline(policy_query: str) -> dict:
    """Run analyst agent first, then housing agent."""
    from backend.agents.run import run_analyst_agent

    print("Step 1: Running Analyst Agent...")
    analyst_result = await run_analyst_agent(policy_query)
    briefing = analyst_result.get("phase_5_output")

    if not briefing:
        print("ERROR: Analyst agent did not produce a briefing.")
        return {}

    print("\nStep 2: Running Housing Agent...")
    return await run_housing_agent(briefing, policy_query)


if __name__ == "__main__":
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Raise the federal minimum wage to $15/hr"
    )
    asyncio.run(_run_full_pipeline(query))

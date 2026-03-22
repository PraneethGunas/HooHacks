"""CLI entry point for the Consumer & Prices sector agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from backend.agents.consumer.graph import build_consumer_graph
from backend.agents.consumer.schemas import ConsumerState
from backend.agents.schemas import AnalystBriefing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def run_consumer_agent(
    analyst_briefing: AnalystBriefing,
    policy_query: str = "",
) -> dict:
    """Run the full 5-phase consumer agent and return the final state."""
    graph = build_consumer_graph()

    query = policy_query
    if not query and analyst_briefing.policy_spec:
        query = f"{analyst_briefing.policy_spec.action}: {analyst_briefing.policy_spec.value}"

    initial_state: ConsumerState = {
        "analyst_briefing": analyst_briefing,
        "policy_query": query,
        "current_phase": 1,
        "phase_1_output": None,
        "phase_2_output": None,
        "phase_3_output": None,
        "phase_4_output": None,
        "phase_5_output": None,
        "phase_2_summary": None,
        "phase_3_summary": None,
        "phase_4_summary": None,
        "tool_call_log": [],
    }

    final_state = await graph.ainvoke(initial_state)

    # Print summary
    report = final_state.get("phase_5_output")
    if report and report.consumer_impact_scorecard and report.consumer_impact_scorecard.scorecards:
        sc = report.consumer_impact_scorecard
        print("\n" + "=" * 60)
        print("CONSUMER IMPACT SCORECARD")
        print("=" * 60)
        for card in sc.scorecards:
            print(f"\n--- {card.region} | {card.income_tier} | {card.household_type} ---")
            print(f"  Income change: {card.total_income_change}")
            print(f"  Cost-of-living change: {card.total_cost_change}")
            print(f"  Net monthly: {card.net_monthly_change}")
            print(f"  Net annual: {card.net_annual_change}")
            print(f"  Verdict: {card.verdict}")
        print(f"\nTool calls: {len(final_state.get('tool_call_log', []))}")
    elif report:
        print("\nConsumer report produced but no scorecard.")
        print(f"Direct effects: {len(report.direct_effects)}")
    else:
        print("\nConsumer agent did not produce a final report. Check logs.")

    return final_state


async def _run_full_pipeline(policy_query: str) -> dict:
    """Run analyst agent first, then consumer agent."""
    from backend.agents.run import run_analyst_agent

    print("Step 1: Running Analyst Agent...")
    analyst_result = await run_analyst_agent(policy_query)
    briefing = analyst_result.get("phase_5_output")

    if not briefing:
        print("ERROR: Analyst agent did not produce a briefing.")
        return {}

    print("\nStep 2: Running Consumer Agent...")
    return await run_consumer_agent(briefing, policy_query)


if __name__ == "__main__":
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Raise the federal minimum wage to $15/hr"
    )
    asyncio.run(_run_full_pipeline(query))

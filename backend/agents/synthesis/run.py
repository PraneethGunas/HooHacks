"""CLI entry point for the Synthesis & Impact Dashboard agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from backend.agents.synthesis.graph import build_synthesis_graph
from backend.agents.synthesis.schemas import SynthesisState
from backend.agents.schemas import AnalystBriefing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def run_synthesis_agent(
    analyst_briefing: AnalystBriefing,
    housing_report=None,
    consumer_report=None,
    policy_query: str = "",
) -> dict:
    """Run the 5-phase synthesis agent and return the final state."""
    graph = build_synthesis_graph()

    query = policy_query
    if not query and analyst_briefing.policy_spec:
        query = f"{analyst_briefing.policy_spec.action}: {analyst_briefing.policy_spec.value}"

    initial_state: SynthesisState = {
        "analyst_briefing": analyst_briefing,
        "housing_report": housing_report,
        "consumer_report": consumer_report,
        "policy_query": query,
        "current_phase": 1,
        "phase_1_output": None,
        "phase_2_output": None,
        "phase_3_output": None,
        "phase_4_output": None,
        "phase_5_output": None,
        "phase_1_summary": None,
        "phase_2_summary": None,
        "phase_3_summary": None,
        "tool_call_log": [],
    }

    final_state = await graph.ainvoke(initial_state)

    # Print summary
    report = final_state.get("phase_5_output")
    if report:
        print("\n" + "=" * 60)
        print("SYNTHESIS REPORT")
        print("=" * 60)
        print(f"\nPolicy: {report.policy_title}")
        print(f"Bottom line: {report.policy_one_liner}")
        if report.narrative:
            print(f"\n{report.narrative.executive_summary}")
            print(f"\nKey findings:")
            for f in report.narrative.key_findings:
                print(f"  - {f}")
        if report.winners_losers:
            print(f"\nWinners:")
            for w in report.winners_losers.winners:
                print(f"  + {w.profile}: {w.net_monthly}")
            print(f"Losers:")
            for l in report.winners_losers.losers:
                print(f"  - {l.profile}: {l.net_monthly}")
            print(f"\nVerdict: {report.winners_losers.distributional_verdict}")
        print(f"\nConfidence: {report.overall_confidence}")
        print(f"Tool calls: {len(final_state.get('tool_call_log', []))}")
    else:
        print("\nSynthesis agent did not produce a report. Check logs.")

    return final_state


async def _run_full_pipeline(policy_query: str) -> dict:
    """Run the full pipeline: analyst → housing + consumer (parallel) → synthesis."""
    from backend.agents.run import run_analyst_agent
    from backend.agents.housing.run import run_housing_agent
    from backend.agents.consumer.run import run_consumer_agent

    # Stage 1: Analyst
    print("=" * 60)
    print("STAGE 1: ANALYST AGENT")
    print("=" * 60)
    analyst_state = await run_analyst_agent(policy_query)
    briefing = analyst_state.get("phase_5_output")
    if not briefing:
        print("ERROR: Analyst failed.")
        return {}

    # Stage 2: Housing + Consumer in PARALLEL
    print("\n" + "=" * 60)
    print("STAGE 2: SECTOR AGENTS (Housing + Consumer in parallel)")
    print("=" * 60)
    housing_task = asyncio.create_task(run_housing_agent(briefing, policy_query))
    consumer_task = asyncio.create_task(run_consumer_agent(briefing, policy_query))

    housing_state, consumer_state = await asyncio.gather(housing_task, consumer_task)

    housing_report = housing_state.get("phase_5_output")
    consumer_report = consumer_state.get("phase_5_output")

    # Stage 3: Synthesis
    print("\n" + "=" * 60)
    print("STAGE 3: SYNTHESIS AGENT")
    print("=" * 60)
    return await run_synthesis_agent(
        analyst_briefing=briefing,
        housing_report=housing_report,
        consumer_report=consumer_report,
        policy_query=policy_query,
    )


if __name__ == "__main__":
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Raise the federal minimum wage to $15/hr"
    )
    asyncio.run(_run_full_pipeline(query))

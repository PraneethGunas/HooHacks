"""CLI entry point for running the analyst agent."""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from backend.agents.graph import AnalystState, build_analyst_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def run_analyst_agent(policy_query: str) -> dict:
    """Run the full 5-phase analyst agent and return the final state."""
    graph = build_analyst_graph()

    initial_state: AnalystState = {
        "policy_query": policy_query,
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
    briefing = final_state.get("phase_5_output")
    if briefing:
        print("\n" + "=" * 60)
        print("ANALYST BRIEFING COMPLETE")
        print("=" * 60)
        print(f"\nExecutive Summary:\n{briefing.executive_summary}")
        print(f"\nKey Findings:")
        for f in briefing.key_findings:
            print(f"  - {f}")
        print(f"\nCritical Uncertainties:")
        for u in briefing.critical_uncertainties:
            print(f"  - {u}")
        print(f"\nSector Exposure:")
        for s in briefing.sector_exposure:
            print(f"  [{s.exposure_level}] {s.sector}: {', '.join(s.primary_channels)}")
        print(f"\nTool calls made: {len(final_state.get('tool_call_log', []))}")
        for tc in final_state.get("tool_call_log", []):
            print(f"  Phase {tc.phase}: {tc.tool_name}({json.dumps(tc.arguments)[:80]})")
    else:
        print("\nAgent did not produce a final briefing. Check logs for errors.")

    return final_state


if __name__ == "__main__":
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Raise the federal minimum wage to $15/hr"
    )
    asyncio.run(run_analyst_agent(query))

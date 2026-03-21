"""Run the analyst agent and dump the full trace of each phase."""

import asyncio
import json
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from backend.agents.graph import build_analyst_graph


async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Raise the federal minimum wage to $15/hr"

    graph = build_analyst_graph()

    initial_state = {
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

    # Dump full trace
    print("\n" + "=" * 80)
    print("FULL PIPELINE TRACE")
    print("=" * 80)

    # Phase 1
    p1 = final_state.get("phase_1_output")
    if p1:
        print("\n" + "=" * 80)
        print("PHASE 1: POLICY SPECIFICATION")
        print("=" * 80)
        print(p1.model_dump_json(indent=2))

    # Phase 2
    p2 = final_state.get("phase_2_output")
    if p2:
        print("\n" + "=" * 80)
        print("PHASE 2: BASELINE & COUNTERFACTUAL")
        print("=" * 80)
        print(p2.model_dump_json(indent=2))

    # Phase 3
    p3 = final_state.get("phase_3_output")
    if p3:
        print("\n" + "=" * 80)
        print("PHASE 3: TRANSMISSION CHANNELS")
        print("=" * 80)
        print(p3.model_dump_json(indent=2))

    # Phase 4
    p4 = final_state.get("phase_4_output")
    if p4:
        print("\n" + "=" * 80)
        print("PHASE 4: EVIDENCE")
        print("=" * 80)
        print(p4.model_dump_json(indent=2))

    # Phase 5
    p5 = final_state.get("phase_5_output")
    if p5:
        print("\n" + "=" * 80)
        print("PHASE 5: FINAL ANALYST BRIEFING")
        print("=" * 80)
        print(p5.model_dump_json(indent=2))

    # Tool call audit
    tool_log = final_state.get("tool_call_log", [])
    print("\n" + "=" * 80)
    print(f"TOOL CALL AUDIT LOG ({len(tool_log)} calls)")
    print("=" * 80)
    for tc in tool_log:
        print(f"  Phase {tc.phase} | {tc.tool_name}({json.dumps(tc.arguments)[:100]})")
        if tc.result_summary:
            print(f"    → {tc.result_summary[:150]}")


asyncio.run(main())

"""Run full analyst → housing pipeline and save every phase output to docs/."""

import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
os.makedirs(DOCS_DIR, exist_ok=True)


def save_phase(filename: str, title: str, content):
    """Save a phase output to a markdown file in docs/."""
    path = os.path.join(DOCS_DIR, filename)
    if hasattr(content, "model_dump_json"):
        json_str = content.model_dump_json(indent=2)
    elif isinstance(content, dict):
        json_str = json.dumps(content, indent=2, default=str)
    elif isinstance(content, list):
        json_str = json.dumps([c.model_dump() if hasattr(c, "model_dump") else c for c in content], indent=2, default=str)
    else:
        json_str = str(content)

    md = f"# {title}\n\n```json\n{json_str}\n```\n"
    with open(path, "w") as f:
        f.write(md)
    print(f"  Saved: {path} ({len(json_str)} chars)")


def save_tool_log(filename: str, tool_log: list):
    """Save tool call audit log."""
    path = os.path.join(DOCS_DIR, filename)
    lines = [f"# Tool Call Audit Log ({len(tool_log)} calls)\n"]
    for tc in tool_log:
        args_str = json.dumps(tc.arguments, default=str)[:120] if hasattr(tc, "arguments") else str(tc)[:120]
        lines.append(f"- **Phase {tc.phase}** | `{tc.tool_name}({args_str})`")
        if tc.result_summary:
            lines.append(f"  - Result: `{tc.result_summary[:150]}`")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {path}")


async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Raise the federal minimum wage to $15/hr"

    # ==============================
    # STEP 1: ANALYST AGENT
    # ==============================
    print("\n" + "=" * 70)
    print("STEP 1: ANALYST AGENT")
    print("=" * 70)

    from backend.agents.run import run_analyst_agent

    analyst_state = await run_analyst_agent(query)

    # Save analyst phases
    if analyst_state.get("phase_1_output"):
        save_phase("analyst_phase1_policy_spec.md", "Analyst Phase 1: Policy Specification", analyst_state["phase_1_output"])
    if analyst_state.get("phase_2_output"):
        save_phase("analyst_phase2_baseline.md", "Analyst Phase 2: Baseline & Counterfactual", analyst_state["phase_2_output"])
    if analyst_state.get("phase_3_output"):
        save_phase("analyst_phase3_transmission.md", "Analyst Phase 3: Transmission Channels", analyst_state["phase_3_output"])
    if analyst_state.get("phase_4_output"):
        save_phase("analyst_phase4_evidence.md", "Analyst Phase 4: Evidence", analyst_state["phase_4_output"])
    if analyst_state.get("phase_5_output"):
        save_phase("analyst_phase5_briefing.md", "Analyst Phase 5: Final Briefing", analyst_state["phase_5_output"])
    if analyst_state.get("tool_call_log"):
        save_tool_log("analyst_tool_log.md", analyst_state["tool_call_log"])

    briefing = analyst_state.get("phase_5_output")
    if not briefing:
        print("\nERROR: Analyst agent did not produce a briefing. Stopping.")
        return

    # ==============================
    # STEP 2: HOUSING AGENT
    # ==============================
    print("\n" + "=" * 70)
    print("STEP 2: HOUSING AGENT")
    print("=" * 70)

    from backend.agents.housing.run import run_housing_agent

    housing_state = await run_housing_agent(briefing, query)

    # Save housing phases
    if housing_state.get("phase_1_output"):
        save_phase("housing_phase1_pathways.md", "Housing Phase 1: Transmission Pathways", housing_state["phase_1_output"])
    if housing_state.get("phase_2_output"):
        save_phase("housing_phase2_baseline.md", "Housing Phase 2: Housing Market Baseline", housing_state["phase_2_output"])
    if housing_state.get("phase_2_summary"):
        path = os.path.join(DOCS_DIR, "housing_phase2_summary.md")
        with open(path, "w") as f:
            f.write(f"# Housing Phase 2: Baseline Summary (LLM-compressed)\n\n{housing_state['phase_2_summary']}\n")
        print(f"  Saved: {path}")
    if housing_state.get("phase_3_output"):
        save_phase("housing_phase3_magnitudes.md", "Housing Phase 3: Magnitude Estimates", housing_state["phase_3_output"])
    if housing_state.get("phase_4_output"):
        save_phase("housing_phase4_distributional.md", "Housing Phase 4: Distributional & Temporal", housing_state["phase_4_output"])
    if housing_state.get("phase_5_output"):
        save_phase("housing_phase5_report.md", "Housing Phase 5: Final Housing Report", housing_state["phase_5_output"])
    if housing_state.get("tool_call_log"):
        save_tool_log("housing_tool_log.md", housing_state["tool_call_log"])

    # ==============================
    # SUMMARY
    # ==============================
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)

    analyst_tools = len(analyst_state.get("tool_call_log", []))
    housing_tools = len(housing_state.get("tool_call_log", []))
    print(f"Analyst agent: {analyst_tools} tool calls")
    print(f"Housing agent: {housing_tools} tool calls")
    print(f"Total: {analyst_tools + housing_tools} tool calls")
    print(f"\nAll outputs saved to: {DOCS_DIR}/")

    # Print scorecard if available
    report = housing_state.get("phase_5_output")
    if report and report.affordability_scorecard and report.affordability_scorecard.sub_markets:
        print("\n" + "=" * 70)
        print("AFFORDABILITY SCORECARD")
        print("=" * 70)
        for sm in report.affordability_scorecard.sub_markets:
            print(f"\n--- {sm.region_name} ---")
            print(f"  Current rent: {sm.current_median_rent}")
            print(f"  Rent-to-income: {sm.current_rent_to_income}")
            print(f"  Policy rent change: {sm.rent_change}")
            print(f"  Net affordability: {sm.net_affordability_shift}")
            print(f"  @$35K: {sm.impact_at_35k}")
            print(f"  @$55K: {sm.impact_at_55k}")
            print(f"  @$85K: {sm.impact_at_85k}")
    else:
        print("\nNo affordability scorecard produced.")
        if report:
            print(f"Direct effects: {len(report.direct_effects)}")
            print(f"Second order: {len(report.second_order_effects)}")


if __name__ == "__main__":
    asyncio.run(main())

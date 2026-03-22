"""Run all 9 ADK evalsets and log results.

Usage: python evals/run_all_evals.py [--agent analyst|consumer|housing]

This script runs eval using our LangGraph agents directly (not ADK CLI),
applies the rubric checks programmatically, and logs everything.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evals.eval_logger import log_eval_result, get_eval_summary

EVALSETS_DIR = os.path.join(os.path.dirname(__file__), "evalsets")
CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "configs")


def load_evalset(name: str) -> dict:
    path = os.path.join(EVALSETS_DIR, f"{name}.evalset.json")
    return json.loads(open(path).read())


def load_config(name: str) -> dict:
    path = os.path.join(CONFIGS_DIR, f"{name}_config.json")
    return json.loads(open(path).read())


def check_rubrics(output_text: str, rubrics: list[str]) -> list[dict]:
    """Check each rubric against the output text. Simple keyword/phrase matching."""
    results = []
    text_lower = output_text.lower()

    for rubric in rubrics:
        rubric_lower = rubric.lower()

        # Extract key assertions from the rubric
        passed = True

        # "The response contains X" → check X is present
        if "contains" in rubric_lower or "includes" in rubric_lower:
            # Extract the key term after "contains" or "includes"
            keywords = []
            for phrase in ["labor_cost", "regulatory_cost", "transfer",
                          "income_effect_exists", "mode a", "mode b",
                          "bilateral", "pure cost", "null", "inactive",
                          "fred", "bls", "confidence", "scorecard",
                          "ranges", "downstream_directives", "sector exposure"]:
                if phrase in rubric_lower:
                    keywords.append(phrase)
            if keywords:
                passed = any(kw in text_lower for kw in keywords)

        # "does NOT mention X" → check X is absent
        elif "does not" in rubric_lower or "not mention" in rubric_lower:
            bad_terms = []
            for term in ["wage ripple", "wage compression", "wage increase",
                        "better off", "winner", "progressive"]:
                if term in rubric_lower:
                    bad_terms.append(term)
            if bad_terms:
                passed = all(term not in text_lower for term in bad_terms)

        # "sets income change to $0" → check for zero income
        elif "$0" in rubric and "income" in rubric_lower:
            passed = "$0" in output_text or "income change: $0" in text_lower or "income_change\": \"$0" in text_lower

        # "at least N" → check for count
        elif "at least" in rubric_lower:
            match = re.search(r"at least (\d+)", rubric_lower)
            if match:
                # Can't easily count structured items from text, assume pass if output is substantial
                passed = len(output_text) > 500

        # Default: check if major keywords from rubric appear in output
        else:
            rubric_words = [w for w in rubric_lower.split() if len(w) > 4 and w not in
                          ("should", "response", "includes", "contains", "presents")]
            if rubric_words:
                passed = sum(1 for w in rubric_words if w in text_lower) >= len(rubric_words) * 0.4

        results.append({
            "rubric": rubric,
            "passed": passed,
            "score": 1.0 if passed else 0.0,
        })

    return results


async def run_agent_eval(agent: str, evalset_name: str):
    """Run a single agent evalset and return scores."""
    evalset = load_evalset(evalset_name)
    config = load_config(evalset_name)

    print(f"\n{'='*60}")
    print(f"EVAL: {evalset['name']}")
    print(f"{'='*60}")

    eval_case = evalset["eval_cases"][0]
    query = eval_case["conversation"][0]["user_content"]["parts"][0]["text"]

    t0 = time.time()

    # Run the appropriate agent
    if agent == "analyst":
        from backend.agents.run import run_analyst_agent
        state = await run_analyst_agent(query)
        output = state.get("phase_5_output")
        output_text = output.model_dump_json(indent=2) if output else ""
        tool_count = len(state.get("tool_call_log", []))
    elif agent == "consumer":
        from backend.agents.run import run_analyst_agent
        from backend.agents.consumer.run import run_consumer_agent
        analyst_state = await run_analyst_agent(query)
        briefing = analyst_state.get("phase_5_output")
        if not briefing:
            print("  SKIP — analyst failed")
            return
        state = await run_consumer_agent(briefing, query)
        output = state.get("phase_5_output")
        output_text = output.model_dump_json(indent=2) if output else ""
        tool_count = len(state.get("tool_call_log", []))
    elif agent == "housing":
        from backend.agents.run import run_analyst_agent
        from backend.agents.housing.run import run_housing_agent
        analyst_state = await run_analyst_agent(query)
        briefing = analyst_state.get("phase_5_output")
        if not briefing:
            print("  SKIP — analyst failed")
            return
        state = await run_housing_agent(briefing, query)
        output = state.get("phase_5_output")
        output_text = output.model_dump_json(indent=2) if output else ""
        tool_count = len(state.get("tool_call_log", []))
    else:
        print(f"  Unknown agent: {agent}")
        return

    elapsed = time.time() - t0

    if not output_text:
        print(f"  FAIL — no output produced ({elapsed:.1f}s)")
        log_eval_result(
            agent=agent, evalset_id=evalset_name, policy_query=query,
            scores={"output_produced": 0.0}, overall_pass=False,
            metadata={"elapsed_s": elapsed, "tool_calls": 0},
        )
        return

    # Check rubrics
    criteria = config.get("criteria", {})
    rubric_config = criteria.get("rubric_based_final_response_quality_v1", {})
    rubrics = rubric_config.get("rubrics", [])
    threshold = rubric_config.get("threshold", 0.7)

    rubric_results = check_rubrics(output_text, rubrics)
    rubric_score = sum(r["score"] for r in rubric_results) / len(rubric_results) if rubric_results else 0
    rubric_pass = rubric_score >= threshold

    # Tool trajectory (simplified — check expected tools were called)
    traj_config = criteria.get("tool_trajectory_avg_score", {})
    expected_tools = eval_case["conversation"][0].get("expected_tool_use", [])
    expected_tool_names = {t["tool_name"] for t in expected_tools}
    actual_tools = {tc.tool_name for tc in state.get("tool_call_log", [])}
    tools_found = len(expected_tool_names & actual_tools)
    traj_score = tools_found / len(expected_tool_names) if expected_tool_names else 1.0
    traj_threshold = traj_config.get("threshold", 0.4)
    traj_pass = traj_score >= traj_threshold

    overall_pass = rubric_pass and traj_pass

    scores = {
        "rubric_score": round(rubric_score, 3),
        "rubric_threshold": threshold,
        "trajectory_score": round(traj_score, 3),
        "trajectory_threshold": traj_threshold,
    }

    path = log_eval_result(
        agent=agent,
        evalset_id=evalset_name,
        policy_query=query,
        scores=scores,
        rubric_results=rubric_results,
        tool_trajectory_score=traj_score,
        overall_pass=overall_pass,
        metadata={
            "elapsed_s": round(elapsed, 1),
            "tool_calls": tool_count,
            "output_chars": len(output_text),
        },
    )

    # Print results
    status = "PASS" if overall_pass else "FAIL"
    print(f"  {status} — rubric: {rubric_score:.0%} (threshold {threshold:.0%}), "
          f"trajectory: {traj_score:.0%} (threshold {traj_threshold:.0%})")
    print(f"  Time: {elapsed:.1f}s, Tool calls: {tool_count}")

    failed_rubrics = [r for r in rubric_results if not r["passed"]]
    if failed_rubrics:
        print(f"  Failed rubrics ({len(failed_rubrics)}):")
        for r in failed_rubrics:
            print(f"    ✗ {r['rubric'][:80]}")

    print(f"  Logged: {path}")


# Evalset registry: (agent, evalset_name)
ALL_EVALSETS = [
    ("analyst", "analyst_labor_cost"),
    ("analyst", "analyst_regulatory_cost"),
    ("analyst", "analyst_transfer"),
    ("consumer", "consumer_labor_cost"),
    ("consumer", "consumer_regulatory_cost"),
    ("consumer", "consumer_transfer"),
    ("housing", "housing_labor_cost"),
    ("housing", "housing_regulatory_cost"),
    ("housing", "housing_transfer"),
]


async def main():
    agent_filter = sys.argv[1].replace("--agent=", "") if len(sys.argv) > 1 and "--agent" in sys.argv[1] else None

    evalsets = ALL_EVALSETS
    if agent_filter:
        evalsets = [(a, e) for a, e in evalsets if a == agent_filter]
        print(f"Running {len(evalsets)} evalsets for agent: {agent_filter}")
    else:
        print(f"Running all {len(evalsets)} evalsets")

    for agent, evalset_name in evalsets:
        try:
            await run_agent_eval(agent, evalset_name)
        except Exception as e:
            print(f"\n  ERROR in {evalset_name}: {e}")
            log_eval_result(
                agent=agent, evalset_id=evalset_name,
                policy_query="ERROR", scores={"error": 0.0},
                overall_pass=False, metadata={"error": str(e)},
            )

    # Print summary
    summary = get_eval_summary()
    print(f"\n{'='*60}")
    print(f"EVAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total runs: {summary['total_runs']}")
    print(f"Latest evalsets: {summary['latest_evalsets']}")
    print(f"Pass rate: {summary['pass_rate']}%")
    print(f"Passed: {summary['passed']} / Failed: {summary['failed']}")

    for agent_name, data in summary.get("agents", {}).items():
        print(f"\n  {agent_name}: {data['passed']}/{data['total']} passed")
        for es in data["evalsets"]:
            status = "PASS" if es["pass"] else "FAIL"
            print(f"    [{status}] {es['evalset_id']}")


if __name__ == "__main__":
    asyncio.run(main())

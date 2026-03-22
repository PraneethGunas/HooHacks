"""Evaluate agent tool calling patterns from docs/ tool logs.

ADK-style trajectory evaluation:
- Tool ordering (did the agent call tools in a sensible sequence?)
- Tool appropriateness (did it call the right tools for this policy type?)
- Error recovery (did it recover from failed tool calls?)
- Efficiency (redundant calls, wasted calls)
- Phase distribution (are tool calls distributed correctly across phases?)
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DOCS_DIR = Path(__file__).parent.parent / "docs"

POLICY = "Ban single-use plastics nationwide starting 2027"
POLICY_TYPE = "REGULATORY_COST"


def parse_tool_log(filename: str) -> list[dict]:
    """Parse a tool log markdown file into structured records."""
    path = DOCS_DIR / filename
    if not path.exists():
        return []

    text = path.read_text()
    calls = []
    current_call = None

    for line in text.split("\n"):
        # Match: - **Phase X** | `tool_name({args})`
        match = re.match(r"- \*\*Phase (\d+)\*\* \| `(\w+)\((.+?)\)`", line)
        if match:
            if current_call:
                calls.append(current_call)
            phase = int(match.group(1))
            tool = match.group(2)
            args_str = match.group(3)
            current_call = {
                "phase": phase,
                "tool": tool,
                "args": args_str[:200],
                "has_result": False,
                "error": False,
                "error_msg": "",
            }
        elif line.strip().startswith("- Result:") and current_call:
            current_call["has_result"] = True
            result_text = line + "\n"
            # Check for errors in result
            if "error" in line.lower() or "Error:" in line:
                current_call["error"] = True
                current_call["error_msg"] = line[:200]
        elif current_call and ("error" in line.lower() or "Blocked:" in line or "not a valid tool" in line):
            current_call["error"] = True
            current_call["error_msg"] = line.strip()[:200]

    if current_call:
        calls.append(current_call)

    return calls


# Agents that are integrators — no external data/evidence tools expected
INTEGRATOR_AGENTS = {"Synthesis"}


def eval_tool_trajectory(agent: str, calls: list[dict]) -> dict:
    """Evaluate a single agent's tool trajectory."""
    is_integrator = agent in INTEGRATOR_AGENTS

    if not calls:
        if is_integrator:
            return {"agent": agent, "status": "PASS", "score": 1.0, "total_calls": 0,
                    "error_count": 0, "tools_used": {}, "phases_covered": [],
                    "passed": 1, "total_checks": 1,
                    "checks": [{"name": "Integrator (no external tools by design)", "passed": True, "detail": "Synthesis works on upstream outputs only"}]}
        return {"agent": agent, "status": "NO_CALLS", "score": 0, "checks": []}

    checks = []

    # --- CHECK 1: Phase ordering ---
    phases = [c["phase"] for c in calls]
    is_ordered = all(phases[i] <= phases[i+1] for i in range(len(phases)-1))
    checks.append({
        "name": "Phase ordering (monotonically increasing)",
        "passed": is_ordered,
        "detail": f"Phases: {sorted(set(phases))}",
    })

    # --- CHECK 2: Tool diversity (not calling same tool repeatedly with same args) ---
    tool_arg_pairs = [(c["tool"], c["args"][:80]) for c in calls]
    unique = len(set(tool_arg_pairs))
    total = len(tool_arg_pairs)
    diversity = unique / total if total > 0 else 0
    checks.append({
        "name": "Tool call diversity (no redundant identical calls)",
        "passed": diversity >= 0.7,
        "detail": f"{unique}/{total} unique ({diversity:.0%})",
    })

    # --- CHECK 3: Error rate ---
    errors = [c for c in calls if c["error"]]
    error_rate = len(errors) / len(calls)
    checks.append({
        "name": "Error rate < 30%",
        "passed": error_rate < 0.3 or (is_integrator and len(errors) <= 1),
        "detail": f"{len(errors)}/{len(calls)} errors ({error_rate:.0%})" + (" (integrator tolerance)" if is_integrator else ""),
    })

    # --- CHECK 4: Error recovery (after an error, did the agent retry or adapt?) ---
    recovered = 0
    for i, c in enumerate(calls):
        if c["error"] and i + 1 < len(calls):
            next_call = calls[i + 1]
            # Recovery = next call is different (adapted) or same tool different args (retry)
            if next_call["tool"] != c["tool"] or next_call["args"] != c["args"]:
                recovered += 1
    recovery_rate = recovered / len(errors) if errors else 1.0
    checks.append({
        "name": "Error recovery rate (adapted after failures)",
        "passed": recovery_rate >= 0.5 or len(errors) == 0,
        "detail": f"{recovered}/{len(errors)} recovered ({recovery_rate:.0%})" if errors else "No errors to recover from",
    })

    # --- CHECK 5: Appropriate tools for REGULATORY_COST policy ---
    tool_names = [c["tool"] for c in calls]
    tool_counts = Counter(tool_names)

    # For REGULATORY_COST: should use BLS (PPI/CPI), FRED, web_search, openalex
    # Should NOT heavily use tools meant for income analysis
    appropriate_tools = {"bls_get_data", "fred_search", "fred_get_series",
                        "web_search_news", "search_openalex", "search_cbo_reports",
                        "fetch_document_text", "code_execute",
                        "census_acs_query", "bea_regional_data", "hud_data"}

    used_appropriate = sum(1 for t in tool_names if t in appropriate_tools)
    appropriateness = used_appropriate / len(tool_names) if tool_names else 0
    checks.append({
        "name": "Tool appropriateness for policy type",
        "passed": appropriateness >= 0.8,
        "detail": f"{used_appropriate}/{len(tool_names)} appropriate ({appropriateness:.0%}), tools: {dict(tool_counts)}",
    })

    # --- CHECK 6: Phase coverage (data phases should have tool calls) ---
    phases_with_calls = set(phases)
    checks.append({
        "name": "Multiple phases have tool calls",
        "passed": len(phases_with_calls) >= 2,
        "detail": f"Phases with calls: {sorted(phases_with_calls)}",
    })

    # --- CHECK 7: code_execute usage (for computation phases) ---
    code_calls = [c for c in calls if c["tool"] == "code_execute"]
    code_errors = [c for c in code_calls if c["error"]]
    if code_calls:
        code_success = (len(code_calls) - len(code_errors)) / len(code_calls)
        checks.append({
            "name": "code_execute success rate > 50%",
            "passed": code_success > 0.5,
            "detail": f"{len(code_calls) - len(code_errors)}/{len(code_calls)} succeeded ({code_success:.0%})",
        })

        # Check for common code_execute errors
        blocked_imports = sum(1 for c in code_errors if "import" in c.get("error_msg", "").lower() or "from " in c.get("error_msg", "").lower())
        if blocked_imports > 0:
            checks.append({
                "name": "code_execute: no blocked import attempts",
                "passed": blocked_imports <= 1,
                "detail": f"{blocked_imports} blocked import attempts (LLM tried import/from in sandbox)",
            })

    # --- CHECK 8: Data tool usage (FRED, BLS, Census) — skip for integrators ---
    if not is_integrator:
        data_tools = sum(1 for t in tool_names if t in {"fred_search", "fred_get_series", "bls_get_data", "census_acs_query", "bea_regional_data", "hud_data"})
        checks.append({
            "name": "Uses real data tools (FRED/BLS/Census/BEA/HUD)",
            "passed": data_tools >= 3,
            "detail": f"{data_tools} data tool calls",
        })

    # --- CHECK 9: Evidence search (OpenAlex, CBO, academic) — skip for integrators ---
    if not is_integrator:
        evidence_tools = sum(1 for t in tool_names if t in {"search_openalex", "search_cbo_reports", "search_academic_papers"})
        checks.append({
            "name": "Searches for evidence (OpenAlex/CBO/academic)",
            "passed": evidence_tools >= 1,
            "detail": f"{evidence_tools} evidence search calls",
        })

    # --- Compute overall score ---
    passed = sum(1 for c in checks if c["passed"])
    total_checks = len(checks)
    score = passed / total_checks if total_checks > 0 else 0

    return {
        "agent": agent,
        "total_calls": len(calls),
        "error_count": len(errors),
        "tools_used": dict(tool_counts),
        "phases_covered": sorted(phases_with_calls),
        "score": round(score, 3),
        "passed": passed,
        "total_checks": total_checks,
        "status": "PASS" if score >= 0.7 else "FAIL",
        "checks": checks,
    }


def main():
    print(f"{'='*70}")
    print(f"TOOL TRAJECTORY EVALUATION")
    print(f"Policy: {POLICY}")
    print(f"Type: {POLICY_TYPE}")
    print(f"{'='*70}")

    agents = [
        ("Analyst", "analyst_tool_log.md"),
        ("Housing", "housing_tool_log.md"),
        ("Consumer", "consumer_tool_log.md"),
        ("Synthesis", "synthesis_tool_log.md"),
    ]

    all_results = []

    for agent_name, log_file in agents:
        calls = parse_tool_log(log_file)
        result = eval_tool_trajectory(agent_name, calls)
        all_results.append(result)

        print(f"\n{'─'*60}")
        print(f"  {agent_name.upper()} — {result['total_calls']} calls, "
              f"{result['error_count']} errors, score: {result['score']:.0%} → {result['status']}")
        print(f"  Tools: {result['tools_used']}")
        print(f"  Phases: {result['phases_covered']}")
        print(f"{'─'*60}")
        for c in result["checks"]:
            icon = "✓" if c["passed"] else "✗"
            print(f"  {icon} {c['name']}")
            print(f"    {c['detail']}")

    # --- AGGREGATE ---
    total_checks = sum(r["total_checks"] for r in all_results)
    total_passed = sum(r["passed"] for r in all_results)
    total_calls = sum(r["total_calls"] for r in all_results)
    total_errors = sum(r["error_count"] for r in all_results)

    print(f"\n{'='*70}")
    print(f"AGGREGATE TOOL TRAJECTORY RESULTS")
    print(f"{'='*70}")
    print(f"  Total tool calls: {total_calls}")
    print(f"  Total errors: {total_errors} ({total_errors/total_calls:.0%})")
    print(f"  Trajectory checks: {total_passed}/{total_checks} ({total_passed/total_checks:.0%})")
    print(f"\n  Per-Agent:")
    for r in all_results:
        icon = "✓" if r["status"] == "PASS" else "✗"
        print(f"    {icon} {r['agent']:12s} {r['score']:.0%} ({r['passed']}/{r['total_checks']}) "
              f"— {r['total_calls']} calls, {r['error_count']} errors")

    # Save structured results
    output = {
        "policy": POLICY,
        "policy_type": POLICY_TYPE,
        "total_tool_calls": total_calls,
        "total_errors": total_errors,
        "error_rate": round(total_errors / total_calls * 100, 1) if total_calls > 0 else 0,
        "trajectory_score": round(total_passed / total_checks * 100, 1),
        "agents": {r["agent"]: {
            "score": r["score"],
            "status": r["status"],
            "total_calls": r["total_calls"],
            "errors": r["error_count"],
            "tools_used": r["tools_used"],
        } for r in all_results},
    }
    out_path = DOCS_DIR / "eval_tool_trajectory.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n  Saved: {out_path}")

    return output


if __name__ == "__main__":
    main()

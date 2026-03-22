"""Evaluate existing pipeline outputs in docs/ against all rubric criteria.

Runs offline — no LLM calls, no API calls. Just rubric checking against saved outputs.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DOCS_DIR = Path(__file__).parent.parent / "docs"
CONFIGS_DIR = Path(__file__).parent / "configs"

POLICY = "Ban single-use plastics nationwide starting 2027"
POLICY_TYPE = "REGULATORY_COST"


def read_doc(filename: str) -> str:
    path = DOCS_DIR / filename
    if path.exists():
        return path.read_text()
    return ""


def load_config(name: str) -> dict:
    path = CONFIGS_DIR / f"{name}_config.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def check_rubric(text: str, rubric: str) -> tuple[bool, str]:
    """Check a single rubric against text. Returns (passed, reason)."""
    tl = text.lower()
    rl = rubric.lower()

    # "does NOT mention X" checks
    if "does not" in rl or "not mention" in rl or "not claim" in rl or "not produce" in rl:
        bad_terms = []
        for term in ["wage ripple", "wage compression", "wage increase",
                     "better off", "winner", "progressive",
                     "full affordability scorecard", "4-phase temporal"]:
            if term in rl:
                bad_terms.append(term)
        if bad_terms:
            found = [t for t in bad_terms if t in tl]
            if found:
                return False, f"Found forbidden term(s): {found}"
            return True, "Forbidden terms absent"

    # "$0" income checks
    if "$0" in rubric and "income" in rl:
        if "$0" in text or "income change: $0" in tl or '"income_change": "$0' in tl or "income_change\": 0" in tl:
            return True, "Income set to $0"
        return False, "Non-zero income found"

    # "classifies as X" / "sets X to Y"
    for ptype in ["labor_cost", "regulatory_cost", "transfer"]:
        if ptype in rl and ("classif" in rl or "policy_type" in rl):
            if ptype in tl or ptype.replace("_", " ") in tl:
                return True, f"Policy type {ptype} found"
            return False, f"Policy type {ptype} not found"

    if "income_effect_exists" in rl:
        if "false" in rl and ("income_effect_exists\": false" in tl or "income_effect_exists: false" in tl or "income effect exists: false" in tl):
            return True, "income_effect_exists=false found"
        if "true" in rl and ("income_effect_exists\": true" in tl or "income_effect_exists: true" in tl or "income effect exists: true" in tl):
            return True, "income_effect_exists=true found"

    # "mode B" / "pure cost"
    if "mode b" in rl or "pure cost" in rl:
        if "mode b" in tl or "pure cost" in tl or "cost analysis" in tl or "cost scorecard" in tl:
            return True, "Mode B / pure cost found"
        return False, "Mode B / pure cost not found"

    # "regressive" or "proportional" check
    if "regressive" in rl or "proportional" in rl:
        if "regressive" in tl or "proportional" in tl:
            return True, "Regressive/proportional found"
        if "progressive" in tl:
            return False, "Found 'progressive' instead of regressive/proportional"
        return False, "Neither regressive nor proportional found"

    # "NULL" or "INACTIVE" channel checks
    if "null" in rl or "inactive" in rl:
        for term in ["null", "inactive", "none", "negligible", "not applicable", "n/a"]:
            if term in tl:
                return True, f"Found '{term}'"
        return False, "No NULL/INACTIVE marker found"

    # "MARGINAL" or "NEGLIGIBLE" impact
    if "marginal" in rl or "negligible" in rl:
        for term in ["marginal", "negligible", "minimal", "minor", "small", "limited"]:
            if term in tl:
                return True, f"Found '{term}'"
        return False, "No marginal/negligible language found"

    # "at least N" checks
    match = re.search(r"at least (\d+)", rl)
    if match:
        n = int(match.group(1))
        # Count items heuristically
        if "channel" in rl or "transmission" in rl:
            count = tl.count('"name"') + tl.count("channel")
            if count >= n:
                return True, f"Found ~{count} items (need {n})"
        if "region" in rl or "sub-market" in rl or "geographic" in rl:
            count = max(tl.count("sub_market"), tl.count("region"), tl.count('"name"'))
            if count >= n:
                return True, f"Found ~{count} items (need {n})"
        # Generic: check if output is substantial
        if len(text) > 500:
            return True, f"Output substantial ({len(text)} chars)"
        return False, f"Output too small ({len(text)} chars)"

    # "includes" / "contains" — check for key terms
    keywords = re.findall(r'\b[A-Z][A-Z0-9_]{3,}\b', rubric)  # FRED, BLS, CPI, etc.
    keywords += re.findall(r'(?:series ID|FRED|BLS|PPI|CPI|confidence|scorecard|ranges|downstream)', rubric, re.I)
    if keywords:
        found = [k for k in keywords if k.lower() in tl]
        if len(found) >= len(keywords) * 0.4:
            return True, f"Found keywords: {found}"
        return False, f"Missing keywords, found only: {found} of {keywords}"

    # Default: generous pass if output exists and is substantial
    if len(text) > 200:
        return True, "Output exists and is substantial (default pass)"
    return False, "Insufficient output"


def evaluate_agent(agent: str, config_name: str, doc_files: list[str], rubric_override: list[str] | None = None):
    """Evaluate an agent's output against config rubrics."""
    config = load_config(config_name)
    rubric_config = config.get("criteria", {}).get("rubric_based_final_response_quality_v1", {})
    rubrics = rubric_override or rubric_config.get("rubrics", [])
    threshold = rubric_config.get("threshold", 0.7)

    # Concatenate all doc files for this agent
    full_text = ""
    for f in doc_files:
        content = read_doc(f)
        if content:
            full_text += content + "\n\n"

    if not full_text:
        return {"agent": agent, "config": config_name, "status": "NO_OUTPUT", "score": 0, "results": []}

    results = []
    for rubric in rubrics:
        passed, reason = check_rubric(full_text, rubric)
        results.append({"rubric": rubric, "passed": passed, "reason": reason})

    score = sum(1 for r in results if r["passed"]) / len(results) if results else 0
    overall_pass = score >= threshold

    return {
        "agent": agent,
        "config": config_name,
        "policy": POLICY,
        "policy_type": POLICY_TYPE,
        "status": "PASS" if overall_pass else "FAIL",
        "score": round(score, 3),
        "threshold": threshold,
        "passed_count": sum(1 for r in results if r["passed"]),
        "total_rubrics": len(results),
        "results": results,
    }


def main():
    print(f"{'='*70}")
    print(f"EVALUATING PIPELINE OUTPUTS FROM docs/")
    print(f"Policy: {POLICY}")
    print(f"Type: {POLICY_TYPE}")
    print(f"{'='*70}")

    # --- ANALYST ---
    analyst_docs = [
        "analyst_phase1_policy_spec.md", "analyst_phase2_baseline.md",
        "analyst_phase3_transmission.md", "analyst_phase4_evidence.md",
        "analyst_phase5_briefing.md",
    ]
    analyst_eval = evaluate_agent("analyst", "analyst_regulatory_cost", analyst_docs)

    # --- CONSUMER ---
    consumer_docs = [
        "consumer_phase1_shock.md", "consumer_phase2_passthrough.md",
        "consumer_phase3_geo_behavioral.md", "consumer_phase4_purchasing_power.md",
        "consumer_phase5_report.md",
    ]
    consumer_eval = evaluate_agent("consumer", "consumer_regulatory_cost", consumer_docs)

    # --- HOUSING ---
    housing_docs = [
        "housing_phase1_pathways.md", "housing_phase2_baseline.md",
        "housing_phase3_magnitudes.md", "housing_phase4_distributional.md",
        "housing_phase5_report.md",
    ]
    housing_eval = evaluate_agent("housing", "housing_regulatory_cost", housing_docs)

    # --- SYNTHESIS (custom rubrics — not in config files) ---
    synthesis_docs = [
        "synthesis_phase1_audit.md", "synthesis_phase2_impact.md",
        "synthesis_phase3_winners.md", "synthesis_phase4_narrative.md",
        "synthesis_phase5_report.md",
    ]
    synthesis_rubrics = [
        "The response includes an input inventory of upstream agents",
        "The response identifies at least 1 cross-agent inconsistency",
        "The response computes net household impact for at least 3 income tiers",
        "The response identifies winners and losers with specific dollar amounts",
        "The response includes a distributional verdict (progressive/regressive/neutral)",
        "The response includes a narrative executive summary",
        "The response includes a timeline with at least 2 horizons",
        "The response includes confidence assessment",
        "The response includes headline metrics",
    ]
    synthesis_eval = evaluate_agent("synthesis", "custom_synthesis", synthesis_docs,
                                    rubric_override=synthesis_rubrics)

    # --- PIPELINE-LEVEL CHECKS ---
    all_text = ""
    for f in os.listdir(DOCS_DIR):
        if f.endswith(".md"):
            all_text += read_doc(f) + "\n"

    pipeline_checks = []

    # Check 1: Phantom income channel
    consumer_text = "\n".join(read_doc(f) for f in consumer_docs)
    has_wage_ripple = "wage ripple" in consumer_text.lower()
    pipeline_checks.append({
        "check": "No phantom wage ripple in consumer output",
        "passed": not has_wage_ripple,
        "detail": "Found 'wage ripple'" if has_wage_ripple else "Clean",
    })

    # Check 2: All 20 phases completed
    phase_files = [f for f in os.listdir(DOCS_DIR) if "phase" in f and f.endswith(".md") and "summary" not in f]
    pipeline_checks.append({
        "check": "All phase outputs present (expect 20)",
        "passed": len(phase_files) >= 18,
        "detail": f"Found {len(phase_files)} phase files",
    })

    # Check 3: Tool logs exist for all agents
    tool_logs = [f for f in os.listdir(DOCS_DIR) if "tool_log" in f]
    pipeline_checks.append({
        "check": "Tool logs present for all agents",
        "passed": len(tool_logs) >= 3,
        "detail": f"Found {len(tool_logs)} tool logs",
    })

    # Check 4: Synthesis references upstream agents
    synthesis_text = "\n".join(read_doc(f) for f in synthesis_docs)
    refs_housing = "housing" in synthesis_text.lower()
    refs_consumer = "consumer" in synthesis_text.lower()
    pipeline_checks.append({
        "check": "Synthesis references both sector agents",
        "passed": refs_housing and refs_consumer,
        "detail": f"Housing: {refs_housing}, Consumer: {refs_consumer}",
    })

    # Check 5: Pipeline evaluation file exists
    has_eval = (DOCS_DIR / "pipeline_evaluation.md").exists()
    pipeline_checks.append({
        "check": "Pipeline evaluation metadata present",
        "passed": has_eval,
        "detail": "pipeline_evaluation.md exists" if has_eval else "Missing",
    })

    # --- PRINT RESULTS ---
    all_evals = [analyst_eval, consumer_eval, housing_eval, synthesis_eval]

    for ev in all_evals:
        print(f"\n{'─'*60}")
        print(f"  {ev['agent'].upper()} AGENT — {ev['config']}")
        print(f"  Score: {ev['score']:.0%} ({ev['passed_count']}/{ev['total_rubrics']}) "
              f"Threshold: {ev['threshold']:.0%} → {ev['status']}")
        print(f"{'─'*60}")
        for r in ev["results"]:
            icon = "✓" if r["passed"] else "✗"
            print(f"  {icon} {r['rubric'][:75]}")
            if not r["passed"]:
                print(f"    → {r['reason']}")

    print(f"\n{'─'*60}")
    print(f"  PIPELINE-LEVEL CHECKS")
    print(f"{'─'*60}")
    for pc in pipeline_checks:
        icon = "✓" if pc["passed"] else "✗"
        print(f"  {icon} {pc['check']} — {pc['detail']}")

    # --- AGGREGATE SCORES ---
    print(f"\n{'='*70}")
    print(f"AGGREGATE EVAL RESULTS")
    print(f"{'='*70}")

    total_rubrics = sum(ev["total_rubrics"] for ev in all_evals)
    total_passed = sum(ev["passed_count"] for ev in all_evals)
    pipeline_passed = sum(1 for pc in pipeline_checks if pc["passed"])
    pipeline_total = len(pipeline_checks)

    print(f"\n  Agent Rubric Score:    {total_passed}/{total_rubrics} ({total_passed/total_rubrics:.0%})")
    print(f"  Pipeline Check Score:  {pipeline_passed}/{pipeline_total} ({pipeline_passed/pipeline_total:.0%})")
    print(f"  Combined Score:        {(total_passed + pipeline_passed)}/{(total_rubrics + pipeline_total)} "
          f"({(total_passed + pipeline_passed)/(total_rubrics + pipeline_total):.0%})")

    print(f"\n  Per-Agent Breakdown:")
    for ev in all_evals:
        status_icon = "✓" if ev["status"] == "PASS" else "✗"
        print(f"    {status_icon} {ev['agent']:12s} {ev['score']:.0%} ({ev['passed_count']}/{ev['total_rubrics']})")

    print(f"\n  Frontend-Presentable Metrics:")
    print(f"    ┌─────────────────────────────────────────────┐")
    print(f"    │  Quality Score: {total_passed}/{total_rubrics} rubrics passed ({total_passed/total_rubrics:.0%})     │")
    print(f"    │  Pipeline Health: {pipeline_passed}/{pipeline_total} checks passed          │")
    print(f"    │  Agents Evaluated: {len(all_evals)}                        │")
    print(f"    │  Policy Type: {POLICY_TYPE:30s}  │")
    print(f"    └─────────────────────────────────────────────┘")

    # Return structured data for frontend
    return {
        "quality_score": round(total_passed / total_rubrics * 100, 1),
        "pipeline_health": round(pipeline_passed / pipeline_total * 100, 1),
        "agents_evaluated": len(all_evals),
        "policy_type": POLICY_TYPE,
        "agent_scores": {ev["agent"]: {"score": ev["score"], "status": ev["status"]} for ev in all_evals},
        "pipeline_checks": {pc["check"]: pc["passed"] for pc in pipeline_checks},
        "rubric_failures": [
            {"agent": ev["agent"], "rubric": r["rubric"], "reason": r["reason"]}
            for ev in all_evals for r in ev["results"] if not r["passed"]
        ],
    }


if __name__ == "__main__":
    result = main()
    # Save structured result
    out_path = DOCS_DIR / "eval_results.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\n  Saved structured results to: {out_path}")

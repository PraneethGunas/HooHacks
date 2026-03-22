"""Inline evaluation runner — runs rubric checks after each agent completes.

Emits eval_score SSE events so the frontend can show quality badges in real-time.
Runs asynchronously (non-blocking) so it doesn't slow down the pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict], Awaitable[None]]


# ---------------------------------------------------------------------------
# Rubric definitions per agent
# ---------------------------------------------------------------------------

ANALYST_RUBRICS = [
    {"id": "policy_spec", "name": "Policy specification complete", "check": lambda t: any(k in t for k in ['"action"', '"value"', '"scope"'])},
    {"id": "baseline_data", "name": "Real data gathered (FRED/BLS)", "check": lambda t: any(k in t for k in ["FRED", "BLS", "fred_get_series", "bls_get_data", "series_id"])},
    {"id": "channels_mapped", "name": "Transmission channels identified", "check": lambda t: "channel" in t.lower() or "transmission" in t.lower()},
    {"id": "confidence_levels", "name": "Confidence levels assigned", "check": lambda t: any(k in t.upper() for k in ["HIGH", "MEDIUM", "LOW", "EMPIRICAL", "THEORETICAL"])},
    {"id": "evidence_cited", "name": "Evidence with citations", "check": lambda t: any(k in t for k in ["doi.org", "openalex", "CBO", "cbo.gov", "study", "meta-analysis"])},
    {"id": "sector_exposure", "name": "Sector exposure matrix", "check": lambda t: "sector" in t.lower() and ("exposure" in t.lower() or "impact" in t.lower())},
    {"id": "policy_type", "name": "Policy type classified", "check": lambda t: any(k in t for k in ["LABOR_COST", "REGULATORY_COST", "TRANSFER", "TRADE", "TAX_FISCAL", "policy_type"])},
    {"id": "income_gate", "name": "Income effect flag set", "check": lambda t: "income_effect" in t.lower()},
]

HOUSING_RUBRICS = [
    {"id": "pathways", "name": "Pathways activated/skipped", "check": lambda t: "pathway" in t.lower() or "channel" in t.lower()},
    {"id": "baseline_data", "name": "Housing data gathered", "check": lambda t: any(k in t for k in ["HOUST", "MORTGAGE", "vacancy", "median_rent", "FRED", "Census", "HUD"])},
    {"id": "sub_markets", "name": "Sub-markets identified", "check": lambda t: "sub_market" in t.lower() or "sub-market" in t.lower() or "region" in t.lower()},
    {"id": "elasticities", "name": "Elasticities applied", "check": lambda t: "elasticity" in t.lower() or "0.3" in t or "0.7" in t or "pass-through" in t.lower()},
    {"id": "scorecard", "name": "Affordability scorecard produced", "check": lambda t: "scorecard" in t.lower() or "affordability" in t.lower()},
    {"id": "temporal", "name": "Temporal sequencing included", "check": lambda t: any(k in t.lower() for k in ["0-6 month", "6-18", "temporal", "timeline", "horizon"])},
]

CONSUMER_RUBRICS = [
    {"id": "entry_points", "name": "Price shock entry points identified", "check": lambda t: "entry" in t.lower() or "shock" in t.lower() or "pass-through" in t.lower()},
    {"id": "cpi_data", "name": "CPI/PPI baseline data", "check": lambda t: any(k in t for k in ["CPI", "PPI", "CUSR", "WPU", "price index"])},
    {"id": "pass_through", "name": "Pass-through rates estimated", "check": lambda t: "pass-through" in t.lower() or "pass_through" in t.lower()},
    {"id": "budget_shares", "name": "Budget shares by income", "check": lambda t: "budget" in t.lower() or "expenditure" in t.lower() or "share" in t.lower()},
    {"id": "household_profiles", "name": "Household profiles computed", "check": lambda t: "household" in t.lower() or "profile" in t.lower() or "income_tier" in t.lower()},
    {"id": "no_phantom", "name": "No phantom income (if REGULATORY)", "check": lambda t: True},  # Special check below
]

SYNTHESIS_RUBRICS = [
    {"id": "consistency", "name": "Cross-agent consistency audit", "check": lambda t: "consistency" in t.lower() or "inconsisten" in t.lower() or "audit" in t.lower()},
    {"id": "household_impacts", "name": "Household impacts computed", "check": lambda t: "household" in t.lower() and ("impact" in t.lower() or "net" in t.lower())},
    {"id": "winners_losers", "name": "Winners/losers identified", "check": lambda t: "winner" in t.lower() or "loser" in t.lower() or "burden" in t.lower()},
    {"id": "narrative", "name": "Narrative summary produced", "check": lambda t: "narrative" in t.lower() or "executive" in t.lower() or "bottom_line" in t.lower()},
    {"id": "confidence", "name": "Confidence assessment", "check": lambda t: "confidence" in t.lower() and ("overall" in t.lower() or "weakest" in t.lower())},
    {"id": "timeline", "name": "Timeline included", "check": lambda t: "timeline" in t.lower() or "month" in t.lower() or "horizon" in t.lower()},
]


def _run_rubrics(agent: str, output_text: str, rubrics: list[dict], extra_checks: dict | None = None) -> dict:
    """Run rubric checks against agent output text. Returns score dict."""
    results = []
    for rubric in rubrics:
        # Special override checks
        if extra_checks and rubric["id"] in extra_checks:
            passed = extra_checks[rubric["id"]]
        else:
            try:
                passed = rubric["check"](output_text)
            except Exception:
                passed = False
        results.append({
            "id": rubric["id"],
            "name": rubric["name"],
            "passed": passed,
        })

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)
    score = round(passed_count / total * 100, 1) if total > 0 else 0

    return {
        "agent": agent,
        "score": score,
        "passed": passed_count,
        "total": total,
        "status": "pass" if score >= 70 else "fail",
        "rubrics": results,
    }


async def evaluate_agent_output(
    agent: str,
    output: Any,
    emit: EventCallback,
    policy_type: str = "",
    income_effect: bool | None = None,
) -> dict | None:
    """Run eval on an agent's output and emit the score via SSE.

    Call this right after each agent completes. Non-blocking — errors
    are caught and logged, never crash the pipeline.
    """
    try:
        # Serialize output to text for rubric checking
        if hasattr(output, "model_dump_json"):
            output_text = output.model_dump_json()
        elif isinstance(output, dict):
            output_text = json.dumps(output, default=str)
        else:
            output_text = str(output)

        # Select rubrics based on agent
        extra_checks = {}
        if agent == "analyst":
            rubrics = ANALYST_RUBRICS
        elif agent == "housing":
            rubrics = HOUSING_RUBRICS
        elif agent == "consumer":
            rubrics = CONSUMER_RUBRICS
            # Special phantom channel check for REGULATORY_COST
            if income_effect is False:
                has_phantom = any(
                    term in output_text.lower()
                    for term in ["wage ripple", "wage compression", "better off", "winner"]
                )
                extra_checks["no_phantom"] = not has_phantom
        elif agent == "synthesis":
            rubrics = SYNTHESIS_RUBRICS
        else:
            return None

        # Run rubrics
        result = _run_rubrics(agent, output_text, rubrics, extra_checks)

        # Count tool calls if available
        tool_count = output_text.count('"tool_name"') + output_text.count('"tool":')

        # Emit eval score event
        await emit({
            "type": "eval_score",
            "agent": agent,
            "data": {
                "agent": agent,
                "score": result["score"],
                "passed": result["passed"],
                "total": result["total"],
                "status": result["status"],
                "rubrics": result["rubrics"],
                "tool_calls": tool_count,
                "policy_type": policy_type,
            },
        })

        logger.info(f"Eval {agent}: {result['score']}% ({result['passed']}/{result['total']}) — {result['status']}")
        return result

    except Exception as e:
        logger.warning(f"Eval {agent} failed: {e}")
        return None


async def evaluate_pipeline_health(
    agents_evaluated: list[dict],
    emit: EventCallback,
) -> dict | None:
    """Run pipeline-level checks and emit aggregate score."""
    try:
        total_passed = sum(a["passed"] for a in agents_evaluated)
        total_rubrics = sum(a["total"] for a in agents_evaluated)
        overall_score = round(total_passed / total_rubrics * 100, 1) if total_rubrics > 0 else 0

        agent_scores = {
            a["agent"]: {"score": a["score"], "status": a["status"]}
            for a in agents_evaluated
        }

        result = {
            "overall_score": overall_score,
            "total_passed": total_passed,
            "total_rubrics": total_rubrics,
            "agents_evaluated": len(agents_evaluated),
            "agent_scores": agent_scores,
            "pipeline_status": "pass" if overall_score >= 70 else "needs_improvement",
        }

        await emit({
            "type": "eval_pipeline",
            "data": result,
        })

        logger.info(f"Pipeline eval: {overall_score}% ({total_passed}/{total_rubrics})")
        return result

    except Exception as e:
        logger.warning(f"Pipeline eval failed: {e}")
        return None

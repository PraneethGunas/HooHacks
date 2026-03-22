"""Eval results logger — stores every evaluation run with scores, per-rubric results, and metadata.

Results are stored as JSON files in evals/results/ with timestamps.
A summary index (evals/results/index.json) tracks all runs for quick lookup.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
INDEX_PATH = RESULTS_DIR / "index.json"


def _load_index() -> list[dict]:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text())
    return []


def _save_index(index: list[dict]):
    INDEX_PATH.write_text(json.dumps(index, indent=2, default=str))


def log_eval_result(
    agent: str,
    evalset_id: str,
    policy_query: str,
    scores: dict,
    rubric_results: list[dict] | None = None,
    tool_trajectory_score: float | None = None,
    hallucination_score: float | None = None,
    overall_pass: bool = True,
    metadata: dict | None = None,
) -> str:
    """Log an evaluation result to disk.

    Args:
        agent: "analyst", "consumer", or "housing"
        evalset_id: e.g., "analyst_labor_cost"
        policy_query: the policy that was evaluated
        scores: dict of criterion_name → score (0-1)
        rubric_results: list of {rubric: str, passed: bool, score: float}
        tool_trajectory_score: trajectory match score (0-1)
        hallucination_score: hallucination detection score (0-1)
        overall_pass: whether all criteria met thresholds
        metadata: extra info (model, timing, etc.)

    Returns:
        Path to the saved result file.
    """
    ts = datetime.now(timezone.utc)
    run_id = f"{evalset_id}_{ts.strftime('%Y%m%d_%H%M%S')}"

    result = {
        "run_id": run_id,
        "timestamp": ts.isoformat(),
        "agent": agent,
        "evalset_id": evalset_id,
        "policy_query": policy_query,
        "overall_pass": overall_pass,
        "scores": scores,
        "rubric_results": rubric_results or [],
        "tool_trajectory_score": tool_trajectory_score,
        "hallucination_score": hallucination_score,
        "metadata": metadata or {},
    }

    # Save individual result
    result_path = RESULTS_DIR / f"{run_id}.json"
    result_path.write_text(json.dumps(result, indent=2, default=str))

    # Update index
    index = _load_index()
    index.append({
        "run_id": run_id,
        "timestamp": ts.isoformat(),
        "agent": agent,
        "evalset_id": evalset_id,
        "overall_pass": overall_pass,
        "scores": scores,
    })
    _save_index(index)

    return str(result_path)


def get_latest_scores(agent: str | None = None) -> list[dict]:
    """Get the most recent eval score for each evalset, optionally filtered by agent."""
    index = _load_index()
    if agent:
        index = [r for r in index if r["agent"] == agent]

    # Group by evalset_id, keep latest
    latest = {}
    for r in index:
        eid = r["evalset_id"]
        if eid not in latest or r["timestamp"] > latest[eid]["timestamp"]:
            latest[eid] = r

    return list(latest.values())


def get_eval_summary() -> dict:
    """Get aggregate eval summary across all agents."""
    index = _load_index()
    if not index:
        return {"total_runs": 0, "pass_rate": 0, "agents": {}}

    latest = {}
    for r in index:
        eid = r["evalset_id"]
        if eid not in latest or r["timestamp"] > latest[eid]["timestamp"]:
            latest[eid] = r

    results = list(latest.values())
    total = len(results)
    passed = sum(1 for r in results if r["overall_pass"])

    by_agent = {}
    for r in results:
        agent = r["agent"]
        if agent not in by_agent:
            by_agent[agent] = {"total": 0, "passed": 0, "evalsets": []}
        by_agent[agent]["total"] += 1
        if r["overall_pass"]:
            by_agent[agent]["passed"] += 1
        by_agent[agent]["evalsets"].append({
            "evalset_id": r["evalset_id"],
            "pass": r["overall_pass"],
            "scores": r.get("scores", {}),
        })

    return {
        "total_runs": len(index),
        "latest_evalsets": total,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "passed": passed,
        "failed": total - passed,
        "agents": by_agent,
    }

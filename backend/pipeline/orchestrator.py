"""
Pipeline orchestrator — runs all stages and streams SSE events.

===========================================================================
INTEGRATION GUIDE
===========================================================================

This orchestrator runs each pipeline stage sequentially:
  Stage 0: Classifier   — extract policy parameters (LLM or keyword fallback)
  Stage 1: Analyst       — gather baseline data from public APIs
  Stage 1.5: Premium     — L402 Lightning payments for gated data (🟢 REAL)
  Stage 2: Sector Agents — 4 parallel LLM analyses (labor, housing, consumer, business)
  Stage 3: Synthesis     — aggregate into final report + Sankey data

CURRENT STATUS:
  - Stages use LLM (Google Gemini / OpenAI / Anthropic) when API keys are set
  - Falls back to curated demo responses for the 3 golden-path scenarios
  - Premium data stage is REAL Lightning L402 payments
  - All stages emit SSE events for real-time frontend display

TO SWAP IN LANGGRAPH (Rudra):
  Each stage function is independent. Replace any stage's implementation
  with a LangGraph node while keeping the same signature:
    async def stage_fn(state, emit) -> state
===========================================================================
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

from backend.models.pipeline import (
    SectorReport,
    SynthesisReport,
)

logger = logging.getLogger(__name__)


# Type alias for the SSE event callback
EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class PipelineState:
    """Mutable state that flows through all pipeline stages."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    user_context: dict[str, Any] = field(default_factory=dict)

    # Stage 0 output
    policy_type: str = ""
    policy_params: dict[str, Any] = field(default_factory=dict)

    # Stage 1 output
    briefing: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    # Stage 1.5 output (premium data)
    premium_data: dict[str, Any] = field(default_factory=dict)
    payments: list[dict[str, Any]] = field(default_factory=list)

    # Stage 2 output
    sector_reports: list[SectorReport] = field(default_factory=list)

    # Stage 3 output (synthesis)
    synthesis: SynthesisReport | None = None

    # Timing
    start_time: float = 0.0
    stage_times: dict[str, float] = field(default_factory=dict)


async def run_pipeline(
    query: str,
    user_context: dict[str, Any] | None = None,
    emit: EventCallback | None = None,
) -> PipelineState:
    """
    Run the full PolicyPulse analysis pipeline.

    Args:
        query: The user's policy question
        user_context: Optional personal context (role, graduation_year, etc.)
        emit: Async callback for SSE events — called with dict matching PipelineEvent schema

    Returns:
        PipelineState with all stage outputs populated
    """
    state = PipelineState(
        query=query,
        user_context=user_context or {},
        start_time=time.time(),
    )

    # --- Event logger: dump every SSE event to debug_output/<session_id>.jsonl ---
    debug_dir = Path(__file__).resolve().parent.parent.parent / "debug_output"
    debug_dir.mkdir(exist_ok=True)
    debug_file = debug_dir / f"{state.session_id}.jsonl"
    logger.info(f"Pipeline events will be saved to {debug_file}")

    def _log_event(event: dict[str, Any]) -> None:
        try:
            with open(debug_file, "a") as f:
                f.write(json.dumps(event, default=str) + "\n")
        except Exception:
            pass  # never let logging break the pipeline

    async def _emit(event: dict[str, Any]) -> None:
        event["timestamp"] = time.time()
        _log_event(event)
        if emit:
            await emit(event)

    # Import stages here to avoid circular imports
    from backend.pipeline.classifier import run_classifier
    from backend.pipeline.analyst import run_analyst
    from backend.pipeline.sector import run_sector_agents
    from backend.pipeline.synthesis import run_synthesis

    try:
        # Stage 0: Classifier
        t0 = time.time()
        state = await run_classifier(state, _emit)
        state.stage_times["classifier"] = time.time() - t0

        # Stage 1: Analyst (data gathering)
        t1 = time.time()
        state = await run_analyst(state, _emit)
        state.stage_times["analyst"] = time.time() - t1

        # Stage 1.5: Premium Data (Lightning L402)
        t15 = time.time()
        state = await _run_premium(state, _emit)
        state.stage_times["premium"] = time.time() - t15

        # Stage 2: Sector Agents (parallel)
        t2 = time.time()
        state = await run_sector_agents(state, _emit)
        state.stage_times["sector"] = time.time() - t2

        # Stage 3: Synthesis
        t3 = time.time()
        state = await run_synthesis(state, _emit)
        state.stage_times["synthesis"] = time.time() - t3

        total = time.time() - state.start_time
        state.stage_times["total"] = total

        await _emit({
            "type": "pipeline_complete",
            "data": {
                "session_id": state.session_id,
                "total_seconds": round(total, 1),
                "stage_times": {k: round(v, 1) for k, v in state.stage_times.items()},
            },
        })

        # Dump final state summary
        try:
            summary = {
                "session_id": state.session_id,
                "query": state.query,
                "policy_type": state.policy_type,
                "policy_params": state.policy_params,
                "briefing_keys": list(state.briefing.keys()) if state.briefing else [],
                "num_tool_calls": len(state.tool_calls),
                "num_sector_reports": len(state.sector_reports),
                "sector_report_sectors": [r.sector if hasattr(r, "sector") else str(r)[:80] for r in state.sector_reports],
                "has_synthesis": state.synthesis is not None,
                "stage_times": {k: round(v, 1) for k, v in state.stage_times.items()},
                "payments": state.payments,
            }
            state_file = debug_dir / f"{state.session_id}_state.json"
            with open(state_file, "w") as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"Pipeline state saved to {state_file}")
        except Exception as e:
            logger.warning(f"Failed to save pipeline state: {e}")

    except Exception as e:
        await _emit({
            "type": "pipeline_error",
            "data": {"error": str(e), "stage": _current_stage(state)},
        })
        raise

    return state


async def _run_premium(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 1.5: Premium data via L402 Lightning payments."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        from backend.lightning.premium_agent import PremiumDataAgent

        agent = PremiumDataAgent()
        result = await agent.run(query=state.query, on_event=emit)
        state.premium_data = result.get("premium_data", {})
        state.payments = result.get("payments", [])
        # Merge premium data into briefing so sector agents can use it
        if state.premium_data:
            state.briefing["premium_data"] = state.premium_data
        await agent.close()
        logger.info(
            f"Premium stage complete: {len(state.payments)} payments, "
            f"{len(state.premium_data)} data sources"
        )
    except Exception as e:
        # Lightning is optional — if it fails, pipeline continues
        logger.error(f"Premium stage failed: {e}", exc_info=True)
        await emit({
            "type": "agent_result",
            "agent": "premium",
            "data": {"status": "error", "error": str(e)},
        })
    return state


def _current_stage(state: PipelineState) -> str:
    """Determine which stage we're in based on what's populated."""
    if state.synthesis:
        return "synthesis"
    if state.sector_reports:
        return "sector"
    if state.briefing:
        return "analyst"
    return "classifier"

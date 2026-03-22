"""
Query endpoint — non-streaming entry point for the pipeline.

===========================================================================
INTEGRATION GUIDE
===========================================================================
STATUS: 🟢 REAL — runs the full pipeline and returns results.

Two modes:
  1. POST /api/analyze — runs pipeline, returns full SynthesisReport
  2. GET /stream — SSE streaming (see sse.py)

Most frontends will use the SSE endpoint for real-time updates.
This endpoint is useful for testing, scripting, and non-interactive use.

OWNER: Praneeth (endpoint) + Rudra (pipeline internals)
===========================================================================
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.models.api import QueryRequest, QueryResponse
from backend.pipeline.orchestrator import run_pipeline

router = APIRouter()


@router.post("/analyze", response_model=None)
async def analyze_policy(request: QueryRequest) -> dict:
    """
    Run the full PolicyPulse analysis pipeline (non-streaming).

    Returns the complete SynthesisReport with all sector reports,
    debate results, and Sankey visualization data.
    """
    state = await run_pipeline(
        query=request.query,
        user_context=request.context.model_dump(exclude_none=True),
    )

    if state.synthesis:
        return state.synthesis.model_dump()

    return {
        "error": "Pipeline did not produce a synthesis report",
        "session_id": state.session_id,
        "stage_times": state.stage_times,
    }


@router.get("/health/pipeline")
async def pipeline_health() -> dict:
    """Check that the pipeline modules are importable."""
    checks = {}
    try:
        from backend.pipeline.classifier import run_classifier
        checks["classifier"] = "ok"
    except Exception as e:
        checks["classifier"] = str(e)
    try:
        from backend.pipeline.analyst import run_analyst
        checks["analyst"] = "ok"
    except Exception as e:
        checks["analyst"] = str(e)
    try:
        from backend.pipeline.sector import run_sector_agents
        checks["sector"] = "ok"
    except Exception as e:
        checks["sector"] = str(e)
    try:
        from backend.pipeline.synthesis import run_synthesis
        checks["synthesis"] = "ok"
    except Exception as e:
        checks["synthesis"] = str(e)
    try:
        from backend.lightning.premium_agent import PremiumDataAgent
        checks["lightning"] = "ok"
    except Exception as e:
        checks["lightning"] = str(e)

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "modules": checks}

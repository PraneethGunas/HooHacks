"""
PolicyPulse — FastAPI entrypoint.

===========================================================================
INTEGRATION GUIDE
===========================================================================

STATUS: 🟡 PLACEHOLDER — Only /health endpoint is live.

WHAT'S REAL:
  - FastAPI app with CORS middleware (ready for frontend at localhost:3000)
  - Health check endpoint

WHAT NEEDS TO BE BUILT:
  1. POST /api/query — Main query endpoint. Accepts user question + context,
     kicks off the agent pipeline, returns a session ID.
     [OWNER: Rudra — wire up agent orchestration]

  2. GET /api/sse/{session_id} — SSE stream for real-time agent updates.
     The PremiumDataAgent already emits SSE-compatible events (see
     premium_agent.py). This route needs to:
       - Create an SSE connection
       - Run the agent pipeline (Analyst → Premium → Sector → Synthesis → Debate)
       - Stream each agent's events to the frontend
     [OWNER: Rudra (pipeline) + Samank (frontend SSE consumption)]

  3. GET /api/results/{session_id} — Fetch final results after pipeline
     completes. Returns the synthesized impact summary + source citations.
     [OWNER: Rudra]

FRONTEND EXPECTS (Samank):
  - SSE events with types: agent_start, agent_result, lightning_payment
  - Final JSON with: summary, confidence_scores, sources, payments
  - See premium_agent.py for the event schema already in use.
===========================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings

app = FastAPI(title="PolicyPulse", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # 🟡 Hardcoded to localhost:3000 — update in config.py
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """🟢 REAL: Health check — used by Docker healthchecks and frontend."""
    return {"status": "ok"}


# ===========================================================================
# 🔴 TODO: Uncomment and build these route modules
#
# OWNER: Rudra (backend API routes) + Samank (frontend integration)
#
# Expected file structure:
#   backend/api/query.py  — POST /api/query handler
#   backend/api/sse.py    — GET /api/sse/{session_id} SSE stream
#
# The PremiumDataAgent (backend/lightning/premium_agent.py) is ready to
# plug into the SSE pipeline — it accepts an on_event callback that emits
# lightning_payment events in real time.
#
# Example wiring in query.py:
#   from backend.lightning.premium_agent import PremiumDataAgent
#   agent = PremiumDataAgent()
#   results = await agent.run(query=user_query, on_event=sse_emit)
# ===========================================================================
# from backend.api.query import router as query_router
# from backend.api.sse import router as sse_router
# app.include_router(query_router, prefix="/api")
# app.include_router(sse_router, prefix="/api")

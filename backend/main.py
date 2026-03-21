"""
PolicyPulse — FastAPI entrypoint.

===========================================================================
INTEGRATION GUIDE
===========================================================================

STATUS: 🟢 LIVE — Full pipeline wired up with SSE streaming.

ENDPOINTS:
  GET  /health             — Health check (Docker, frontend)
  GET  /api/health/pipeline — Check all pipeline modules are importable
  GET  /stream?query=...   — SSE stream of the full analysis pipeline
  POST /api/analyze         — Non-streaming: run pipeline, return full report

SSE STREAM (primary frontend integration):
  Samank's frontend connects to GET /stream?query=<policy question>
  Events stream in real time as each stage completes.
  See backend/api/sse.py for event types and format.

NON-STREAMING:
  POST /api/analyze with JSON body: {"query": "...", "context": {...}}
  Returns the full SynthesisReport when pipeline completes.
===========================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api.sse import router as sse_router
from backend.api.query import router as query_router

app = FastAPI(title="PolicyPulse", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(sse_router)             # GET /stream
app.include_router(query_router, prefix="/api")  # POST /api/analyze, GET /api/health/pipeline


@app.get("/health")
async def health():
    """Health check — used by Docker healthchecks and frontend."""
    return {"status": "ok"}

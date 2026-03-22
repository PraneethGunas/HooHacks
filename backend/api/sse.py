"""
SSE streaming endpoint — connects the pipeline to the frontend.

===========================================================================
INTEGRATION GUIDE
===========================================================================
STATUS: 🟢 REAL — streams live pipeline events via Server-Sent Events.

Samank's frontend connects to:
  GET /stream?query=...&context=...

This route:
  1. Starts the pipeline in a background task
  2. Each pipeline stage emits events via the callback
  3. Events are streamed to the frontend as SSE

Event format (matches frontend types in pipeline.ts):
  data: {"type": "classifier_complete", "agent": "classifier", "data": {...}, "timestamp": 1234567890.0}

OWNER: Praneeth (endpoint) + Samank (frontend consumption)
===========================================================================
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Query
from starlette.responses import StreamingResponse

from backend.pipeline.orchestrator import run_pipeline

router = APIRouter()


async def _event_stream(
    query: str,
    user_context: dict[str, Any],
) -> AsyncGenerator[str, None]:
    """Generate SSE events from the pipeline."""
    event_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def emit(event: dict[str, Any]) -> None:
        await event_queue.put(event)

    async def run_and_signal_done() -> None:
        try:
            await run_pipeline(query=query, user_context=user_context, emit=emit)
        except Exception as e:
            await event_queue.put({
                "type": "pipeline_error",
                "data": {"error": str(e)},
                "timestamp": time.time(),
            })
        finally:
            await event_queue.put(None)  # sentinel to stop the stream

    # Start pipeline as a background task
    task = asyncio.create_task(run_and_signal_done())

    try:
        while True:
            event = await event_queue.get()
            if event is None:
                break
            # Format as SSE
            data = json.dumps(event, default=str)
            yield f"data: {data}\n\n"
    finally:
        if not task.done():
            task.cancel()


@router.get("/stream")
async def stream_pipeline(
    query: str = Query(..., min_length=10, description="The policy question"),
    role: str = Query(None, description="User role (student, business owner, etc.)"),
    graduation_year: int = Query(None, description="Graduation year"),
    field: str = Query(None, description="Field of study/work"),
    location: str = Query(None, description="User location"),
    concern: str = Query(None, description="Primary concern"),
) -> StreamingResponse:
    """
    Stream the full analysis pipeline as Server-Sent Events.

    The frontend connects to this endpoint and receives real-time events
    as each pipeline stage completes. Events include classifier results,
    analyst tool calls, Lightning payments, sector reports, debate
    challenges, and the final synthesis.
    """
    user_context = {
        k: v for k, v in {
            "role": role,
            "graduation_year": graduation_year,
            "field": field,
            "location": location,
            "concern": concern,
        }.items() if v is not None
    }

    return StreamingResponse(
        _event_stream(query=query, user_context=user_context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )

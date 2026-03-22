"""
API request/response models for the PolicyPulse endpoints.

Frontend (Samank) sends queries here; the SSE stream uses PipelineEvent
as its event schema.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """Optional personal context the user provides for personalized analysis."""
    role: str | None = None          # "student", "small business owner", etc.
    graduation_year: int | None = None
    field: str | None = None         # "computer science", "electronics import", etc.
    location: str | None = None
    concern: str | None = None       # free-text: what they're most worried about
    extra: dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    """POST /api/analyze request body."""
    query: str = Field(..., min_length=10, max_length=2000, description="The policy question")
    context: UserContext = Field(default_factory=UserContext)


class QueryResponse(BaseModel):
    """POST /api/analyze response — just the session ID to connect SSE."""
    session_id: str
    status: str = "started"


class PipelineEvent(BaseModel):
    """
    SSE event schema — every event the backend streams to the frontend.

    Event types match what Samank's frontend expects:
      - classifier_complete
      - analyst_tool_call, analyst_complete
      - lightning_payment
      - sector_agent_started, sector_agent_tool_call, sector_agent_complete
      - debate_challenge, revision_complete
      - synthesis_complete
      - pipeline_error
    """
    type: str
    agent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float | None = None  # filled automatically by SSE endpoint

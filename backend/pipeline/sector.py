"""
Stage 2: Sector Agents — 4 parallel LLM analyses.

Each sector agent receives the briefing packet and produces a structured
SectorReport with CausalClaims. All 4 run simultaneously.

===========================================================================
INTEGRATION GUIDE
===========================================================================
OWNER: Rudra — swap with LangGraph ReAct agents if time permits.

Currently each agent is a single LLM call with a detailed system prompt.
The prompt enforces structured output matching the SectorReport schema.

Each agent can also make additional tool calls (FRED, BLS) for sector-
specific data. Currently this is done via the LLM requesting data in
its response, which we parse. With LangGraph, these become real ReAct
tool-use loops.
===========================================================================
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

from backend.models.pipeline import (
    CausalClaim,
    ConfidenceLevel,
    SectorReport,
    ToolCallRecord,
)
from backend.pipeline.orchestrator import PipelineState
from backend.pipeline.llm import llm_chat, parse_json_response

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]

SECTORS = ["labor", "housing", "consumer", "business"]

# ---------------------------------------------------------------------------
# System prompts for each sector agent
# ---------------------------------------------------------------------------

SECTOR_PROMPTS = {
    "labor": """You are the LABOR sector analyst in a multi-agent policy analysis system.
Your focus: employment, wages, workforce participation, job creation/destruction, labor mobility.

Given a policy briefing, produce a structured analysis as JSON with this exact schema:
{
  "sector": "labor",
  "direct_effects": [<CausalClaim objects>],
  "second_order_effects": [<CausalClaim objects>],
  "feedback_loops": [<CausalClaim objects>],
  "cross_sector_dependencies": ["list of dependencies on other sectors"],
  "dissent": "optional dissenting view or null"
}

Each CausalClaim MUST have:
{
  "claim": "The assertion",
  "cause": "What drives this effect",
  "effect": "What changes",
  "mechanism": "HOW cause leads to effect — MANDATORY, be specific",
  "confidence": "empirical" | "theoretical" | "speculative",
  "evidence": ["citations from the briefing data"],
  "assumptions": ["what you're taking as given"],
  "sensitivity": "if X changes, this conclusion breaks" or null
}

Rules:
- EMPIRICAL claims must cite specific data from the briefing
- THEORETICAL claims must name the economic model/theory
- SPECULATIVE claims must be explicitly flagged
- Every claim MUST have a mechanism — no "X leads to Y" without HOW
- Produce 2-4 direct effects, 1-3 second-order effects, 1-2 feedback loops""",

    "housing": """You are the HOUSING sector analyst in a multi-agent policy analysis system.
Your focus: housing demand, rent levels, home prices, geographic mobility, housing supply.

Given a policy briefing, produce a structured analysis as JSON with this exact schema:
{
  "sector": "housing",
  "direct_effects": [<CausalClaim objects>],
  "second_order_effects": [<CausalClaim objects>],
  "feedback_loops": [<CausalClaim objects>],
  "cross_sector_dependencies": ["dependencies on labor, consumer, business sectors"],
  "dissent": "optional dissenting view or null"
}

Each CausalClaim MUST have all fields: claim, cause, effect, mechanism (MANDATORY), confidence, evidence, assumptions, sensitivity.

Rules:
- EMPIRICAL: cite specific data. THEORETICAL: name the model. SPECULATIVE: flag explicitly.
- Every claim needs a mechanism. Produce 2-4 direct, 1-3 second-order, 1-2 feedback loops.""",

    "consumer": """You are the CONSUMER sector analyst in a multi-agent policy analysis system.
Your focus: consumer prices, purchasing power, spending patterns, cost of living, inflation pass-through.

Given a policy briefing, produce a structured analysis as JSON with this exact schema:
{
  "sector": "consumer",
  "direct_effects": [<CausalClaim objects>],
  "second_order_effects": [<CausalClaim objects>],
  "feedback_loops": [<CausalClaim objects>],
  "cross_sector_dependencies": ["dependencies on labor, housing, business sectors"],
  "dissent": "optional dissenting view or null"
}

Each CausalClaim MUST have all fields: claim, cause, effect, mechanism (MANDATORY), confidence, evidence, assumptions, sensitivity.

Rules:
- EMPIRICAL: cite specific data. THEORETICAL: name the model. SPECULATIVE: flag explicitly.
- Every claim needs a mechanism. Produce 2-4 direct, 1-3 second-order, 1-2 feedback loops.""",

    "business": """You are the BUSINESS sector analyst in a multi-agent policy analysis system.
Your focus: firm margins, business closures, automation incentives, regional disparities, market competition.

Given a policy briefing, produce a structured analysis as JSON with this exact schema:
{
  "sector": "business",
  "direct_effects": [<CausalClaim objects>],
  "second_order_effects": [<CausalClaim objects>],
  "feedback_loops": [<CausalClaim objects>],
  "cross_sector_dependencies": ["dependencies on labor, housing, consumer sectors"],
  "dissent": "optional dissenting view or null"
}

Each CausalClaim MUST have all fields: claim, cause, effect, mechanism (MANDATORY), confidence, evidence, assumptions, sensitivity.

Rules:
- EMPIRICAL: cite specific data. THEORETICAL: name the model. SPECULATIVE: flag explicitly.
- Every claim needs a mechanism. Produce 2-4 direct, 1-3 second-order, 1-2 feedback loops.""",
}


# ---------------------------------------------------------------------------
# Fallback demo responses (when no LLM key is available)
# ---------------------------------------------------------------------------

def _fallback_report(sector: str, state: PipelineState) -> SectorReport:
    """Generate a minimal demo SectorReport without LLM."""
    return SectorReport(
        sector=sector,
        direct_effects=[
            CausalClaim(
                claim=f"Policy directly affects {sector} sector",
                cause=state.policy_params.get("policy_name", "policy change"),
                effect=f"Changes in {sector} sector conditions",
                mechanism=f"Direct regulatory/economic channel affecting {sector} participants",
                confidence=ConfidenceLevel.THEORETICAL,
                evidence=[],
                assumptions=["Policy is implemented as described"],
            ),
        ],
        second_order_effects=[
            CausalClaim(
                claim=f"Ripple effects propagate through {sector} supply chains",
                cause=f"Initial {sector} disruption",
                effect="Adjustment in related markets",
                mechanism=f"Market participants in {sector} adjust behavior in response to changed incentives",
                confidence=ConfidenceLevel.SPECULATIVE,
                evidence=[],
                assumptions=["Markets adjust within 6-12 months"],
            ),
        ],
        feedback_loops=[],
        cross_sector_dependencies=[s for s in SECTORS if s != sector],
        dissent=None,
    )


def _normalize_confidence(raw_value: str) -> ConfidenceLevel:
    """Map LLM confidence strings to our enum, handling creative LLM outputs."""
    v = raw_value.lower().strip()
    # Direct match
    try:
        return ConfidenceLevel(v)
    except ValueError:
        pass
    # Common LLM variants
    if v in ("high", "strong", "data-backed", "data_backed", "evidence-based"):
        return ConfidenceLevel.EMPIRICAL
    if v in ("medium", "moderate", "model-based", "model_based"):
        return ConfidenceLevel.THEORETICAL
    if v in ("low", "weak", "uncertain", "unknown"):
        return ConfidenceLevel.SPECULATIVE
    return ConfidenceLevel.THEORETICAL  # safe default


def _parse_sector_report(sector: str, raw: str) -> SectorReport:
    """Parse LLM JSON output into a SectorReport."""
    try:
        data = parse_json_response(raw)
    except Exception:
        return SectorReport(sector=sector)

    def _to_list(val: Any) -> list[str]:
        """Coerce LLM output to a list of strings."""
        if isinstance(val, list):
            return [str(v) for v in val]
        if isinstance(val, str) and val:
            return [val]
        return []

    def _parse_claim(c: dict) -> CausalClaim:
        return CausalClaim(
            claim=c.get("claim", ""),
            cause=c.get("cause", ""),
            effect=c.get("effect", ""),
            mechanism=c.get("mechanism", "unspecified"),
            confidence=_normalize_confidence(c.get("confidence", "speculative")),
            evidence=_to_list(c.get("evidence", [])),
            assumptions=_to_list(c.get("assumptions", [])),
            sensitivity=c.get("sensitivity"),
        )

    return SectorReport(
        sector=sector,
        direct_effects=[_parse_claim(c) for c in data.get("direct_effects", [])],
        second_order_effects=[_parse_claim(c) for c in data.get("second_order_effects", [])],
        feedback_loops=[_parse_claim(c) for c in data.get("feedback_loops", [])],
        cross_sector_dependencies=data.get("cross_sector_dependencies", []),
        dissent=data.get("dissent"),
    )


async def _run_one_sector(
    sector: str,
    state: PipelineState,
    emit: EventCallback,
) -> SectorReport:
    """Run a single sector agent."""
    await emit({
        "type": "sector_agent_started",
        "agent": sector,
        "data": {
            "sector": sector,
            "agent": sector.title(),  # Frontend expects capitalized agent name
        },
    })

    # Build the user prompt with briefing data
    briefing_str = json.dumps(state.briefing, default=str)[:6000]
    user_prompt = (
        f"Policy question: {state.query}\n"
        f"Policy classification: {json.dumps(state.policy_params)}\n"
        f"User context: {json.dumps(state.user_context)}\n\n"
        f"Briefing packet (from Analyst Agent):\n{briefing_str}"
    )

    report: SectorReport
    try:
        raw = await llm_chat(
            system_prompt=SECTOR_PROMPTS[sector],
            user_prompt=user_prompt,
            json_mode=True,
            temperature=0.3,
            max_tokens=8000,
        )
        if raw:
            report = _parse_sector_report(sector, raw)
        else:
            report = _fallback_report(sector, state)
    except Exception:
        report = _fallback_report(sector, state)

    # Emit completion with both backend and frontend expected shapes
    await emit({
        "type": "sector_agent_complete",
        "agent": sector,
        "data": {
            # Frontend-expected fields
            "agent": sector.title(),
            "report": report.model_dump(),
            # Keep backend fields for backward compat
            "sector": sector,
            "direct_effects": len(report.direct_effects),
            "second_order_effects": len(report.second_order_effects),
            "feedback_loops": len(report.feedback_loops),
            "has_dissent": report.dissent is not None,
        },
    })

    return report


async def run_sector_agents(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 2: Run all 4 sector agents in parallel."""
    tasks = [
        _run_one_sector(sector, state, emit)
        for sector in SECTORS
    ]
    reports = await asyncio.gather(*tasks, return_exceptions=True)

    state.sector_reports = []
    for sector, result in zip(SECTORS, reports):
        if isinstance(result, Exception):
            state.sector_reports.append(_fallback_report(sector, state))
        else:
            state.sector_reports.append(result)

    return state

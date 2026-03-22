"""
Stage 3: Synthesis Agent — 5-phase LangGraph agentic pipeline.

Uses Rudra's LangGraph synthesis agent (backend/agents/synthesis/) which runs:
  Phase 1: Consistency Audit (reasoning — cross-agent validation)
  Phase 2: Net Household Impact (ReAct — code_execute for math)
  Phase 3: Winners & Losers (ReAct — code_execute)
  Phase 4: Narrative & Timeline (reasoning only)
  Phase 5: Analytics Payload (ReAct — final structuring)

Falls back to simple single-LLM-call synthesis if LangGraph is unavailable.

===========================================================================
INTEGRATION GUIDE
===========================================================================
The agentic synthesis takes AnalystBriefing + HousingReport + ConsumerReport
as structured inputs. The pipeline adapter converts:
  - state.briefing (dict) → AnalystBriefing (via langgraph_adapter)
  - sector_reports → HousingReport / ConsumerReport (if agentic agents ran)

The output SynthesisReport from the agent is converted to the frontend's
expected event shape (policy_summary, unified_impact, impact_dashboard, etc.)

OWNER: Rudra (agent quality) + Praneeth (pipeline integration + SSE)
===========================================================================
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Awaitable, Callable

from backend.models.pipeline import (
    SynthesisReport as PipelineSynthesisReport,
    PolicySummary,
    UnifiedImpact,
    SankeyData,
    SankeyNode,
    SankeyLink,
)
from backend.pipeline.orchestrator import PipelineState
from backend.pipeline.llm import llm_chat, parse_json_response

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]

# Phase metadata for SSE events
SYNTHESIS_PHASES = {
    1: {"name": "Consistency Audit", "type": "reasoning"},
    2: {"name": "Net Household Impact", "type": "react"},
    3: {"name": "Winners & Losers", "type": "react"},
    4: {"name": "Narrative & Timeline", "type": "reasoning"},
    5: {"name": "Analytics Payload", "type": "react"},
}


async def run_synthesis(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 3: Run synthesis — try agentic LangGraph first, fall back to simple."""
    await emit({
        "type": "agent_start",
        "agent": "synthesis",
        "data": {
            "sectors_analyzed": len(state.sector_reports),
            "phases": len(SYNTHESIS_PHASES),
        },
    })

    try:
        state = await _run_langgraph_synthesis(state, emit)
    except Exception as e:
        logger.warning(f"LangGraph synthesis failed ({e}), falling back to simple synthesis")
        state = await _run_simple_synthesis(state, emit)

    return state


# ---------------------------------------------------------------------------
# LangGraph agentic synthesis (primary path)
# ---------------------------------------------------------------------------

async def _run_langgraph_synthesis(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Run Rudra's 5-phase LangGraph synthesis agent with SSE events."""
    from backend.agents.synthesis.graph import build_synthesis_graph
    from backend.agents.synthesis.schemas import SynthesisState, SynthesisReport as AgentSynthesisReport
    from backend.agents.schemas import AnalystBriefing
    from backend.pipeline.langgraph_adapter import briefing_dict_to_analyst_briefing

    # Convert pipeline state → synthesis agent inputs
    analyst_briefing = briefing_dict_to_analyst_briefing(state.briefing)

    # Extract housing/consumer reports if available from agentic sector agents
    housing_report = None
    consumer_report = None
    for report in state.sector_reports:
        if report.sector == "housing" and hasattr(report, "_agentic_report"):
            housing_report = report._agentic_report
        if report.sector == "consumer" and hasattr(report, "_agentic_report"):
            consumer_report = report._agentic_report

    graph = build_synthesis_graph()

    initial_state: SynthesisState = {
        "analyst_briefing": analyst_briefing,
        "housing_report": housing_report,
        "consumer_report": consumer_report,
        "policy_query": state.query,
        "current_phase": 1,
        "phase_1_output": None,
        "phase_2_output": None,
        "phase_3_output": None,
        "phase_4_output": None,
        "phase_5_output": None,
        "phase_1_summary": None,
        "phase_2_summary": None,
        "phase_3_summary": None,
        "tool_call_log": [],
    }

    # Stream through graph with SSE events per phase
    current_phase = 0
    phase_start_times: dict[int, float] = {}

    async def _think(step_type: str, content: str, phase: int, tool: str | None = None) -> None:
        """Emit a thinking event for the synthesis spotlight stream."""
        await emit({
            "type": "synthesis_thinking",
            "agent": "synthesis",
            "data": {
                "step_type": step_type,
                "content": content,
                "phase": str(phase),
                "tool": tool,
            },
        })

    async for event in graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            new_phase = node_output.get("current_phase", current_phase)

            if new_phase != current_phase:
                # Complete previous phase
                if current_phase > 0 and current_phase in phase_start_times:
                    duration = time.time() - phase_start_times[current_phase]
                    await _think("phase_complete", f"Phase {current_phase} ({SYNTHESIS_PHASES.get(current_phase, {}).get('name', '')}) complete in {duration:.1f}s", current_phase)
                    await emit({
                        "type": "synthesis_phase",
                        "agent": "synthesis",
                        "data": {
                            "phase": current_phase,
                            "status": "complete",
                            "name": SYNTHESIS_PHASES.get(current_phase, {}).get("name", ""),
                            "duration_s": round(duration, 1),
                        },
                    })

                # Start new phase
                current_phase = new_phase
                if current_phase <= 5:
                    phase_meta = SYNTHESIS_PHASES.get(current_phase, {})
                    phase_start_times[current_phase] = time.time()
                    await _think("phase_start", f"Phase {current_phase}/5: {phase_meta.get('name', '')} ({phase_meta.get('type', '')})", current_phase)
                    await emit({
                        "type": "synthesis_phase",
                        "agent": "synthesis",
                        "data": {
                            "phase": current_phase,
                            "status": "running",
                            "name": phase_meta.get("name", ""),
                            "type": phase_meta.get("type", ""),
                        },
                    })

            # Emit reasoning content from phase summaries
            for summary_key in ["phase_1_summary", "phase_2_summary", "phase_3_summary"]:
                summary = node_output.get(summary_key)
                if summary and isinstance(summary, str):
                    phase_num = int(summary_key.split("_")[1])
                    await _think("reasoning", summary[:400], phase_num)

            # Emit tool call log entries
            tool_log = node_output.get("tool_call_log", [])
            if tool_log:
                # Only emit new entries (tool_call_log is cumulative)
                for record in tool_log:
                    if hasattr(record, "tool_name"):
                        await _think("tool_call", f"{record.tool_name}({json.dumps(record.arguments)[:150] if record.arguments else ''})", current_phase, record.tool_name)
                        if hasattr(record, "result_summary") and record.result_summary:
                            await _think("tool_result", record.result_summary[:200], current_phase, record.tool_name)

            # Check for final report
            agent_report = node_output.get("phase_5_output")
            if agent_report is not None:
                if current_phase in phase_start_times:
                    duration = time.time() - phase_start_times[current_phase]
                    await _think("phase_complete", f"Phase 5 (Analytics Payload) complete in {duration:.1f}s", 5)
                    await emit({
                        "type": "synthesis_phase",
                        "agent": "synthesis",
                        "data": {
                            "phase": 5,
                            "status": "complete",
                            "name": "Analytics Payload",
                            "duration_s": round(duration, 1),
                        },
                    })

                # Convert agentic report → frontend event shape
                report_data = _convert_agent_report(agent_report, state)

                state.synthesis = PipelineSynthesisReport(
                    policy_summary=PolicySummary(
                        policy_name=agent_report.policy_title or state.policy_params.get("policy_name", "Policy"),
                        parameters=state.policy_params.get("parameters", {}),
                        affected_populations=state.policy_params.get("affected_populations", []),
                    ),
                    agreed_findings=[],
                    disagreements=[],
                    challenge_survival=[],
                    unified_impact=UnifiedImpact(
                        summary=agent_report.narrative.executive_summary if agent_report.narrative else agent_report.policy_one_liner,
                        key_findings=agent_report.narrative.key_findings if agent_report.narrative else [],
                        confidence_breakdown=_count_confidences(state),
                    ),
                    sankey_data=_build_sankey_data(state, None),
                    sector_reports=state.sector_reports,
                    metadata={
                        "session_id": state.session_id,
                        "stage_times": state.stage_times,
                        "total_tool_calls": len(state.tool_calls),
                        "total_payments": len(state.payments),
                        "total_sats_paid": sum(p.get("amount_sats", 0) for p in state.payments),
                    },
                )

                await emit({
                    "type": "synthesis_complete",
                    "agent": "synthesis",
                    "data": {"report": report_data},
                })

    return state


def _convert_agent_report(agent_report: Any, state: PipelineState) -> dict[str, Any]:
    """Convert Rudra's SynthesisReport → new frontend SynthesisReport schema.

    The frontend expects the full Rudra schema shape: meta, policy, headline,
    headline_metrics, waterfall, impact_matrix, category_breakdown, timeline,
    winners_losers, geographic_impact, consistency_report, confidence_assessment,
    evidence_summary, data_sources, narrative.

    The agent's Pydantic SynthesisReport has most data but in a slightly different
    shape. This converter bridges the gap, providing sensible defaults for any
    sections the agent couldn't produce.
    """
    import datetime

    duration_s = int(sum(state.stage_times.values())) if state.stage_times else 0

    # --- meta ---
    meta = {
        "version": "1.0",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pipeline_duration_seconds": duration_s,
        "total_tool_calls": len(state.tool_calls),
        "agents_completed": ["policy_analyst"] + [r.sector for r in state.sector_reports],
        "agents_missing": [],
        "model_used": "gemini-2.5-flash",
        "query": state.query,
    }

    # --- policy ---
    policy = {
        "title": agent_report.policy_title or state.policy_params.get("policy_name", "Policy"),
        "one_liner": agent_report.policy_one_liner or state.query,
        "type": state.policy_params.get("type", "other"),
        "geography": state.policy_params.get("scope", "Federal — United States"),
        "effective_date": None,
        "current_baseline": state.policy_params.get("current_baseline", ""),
        "proposed_change": state.policy_params.get("proposed_change", ""),
        "estimated_annual_cost": state.policy_params.get("estimated_annual_cost", ""),
        "key_ambiguities": state.policy_params.get("key_ambiguities", []),
        "working_assumptions": state.policy_params.get("working_assumptions", []),
    }

    # --- headline ---
    narrative = agent_report.narrative
    headline = {
        "verdict": narrative.bottom_line[:80] if narrative and narrative.bottom_line else "Analysis complete",
        "bottom_line": narrative.executive_summary if narrative else agent_report.policy_one_liner or "",
        "confidence": agent_report.overall_confidence or "MEDIUM",
        "confidence_explanation": agent_report.weakest_component or "",
    }

    # --- headline_metrics ---
    headline_metrics = []
    for i, m in enumerate(agent_report.headline_metrics or []):
        headline_metrics.append({
            "id": f"metric_{i}",
            "label": m.label,
            "value": m.value,
            "range": None,
            "unit": "text",
            "direction": m.direction or "neutral",
            "confidence": (m.confidence or "MEDIUM").upper(),
            "icon": "trending_up" if m.direction == "positive" else "trending_down" if m.direction == "negative" else "info",
            "context": m.context or "",
        })

    # --- waterfall ---
    waterfall_data = agent_report.waterfall
    waterfall_steps = []
    if waterfall_data and waterfall_data.steps:
        cumulative = 0
        for step in waterfall_data.steps:
            cumulative += step.value
            waterfall_steps.append({
                "label": step.label,
                "value": step.value,
                "cumulative": round(cumulative, 2),
                "type": step.type or ("inflow" if step.value > 0 else "outflow" if step.value < 0 else "neutral"),
                "source_agent": "synthesis",
                "note": None,
            })
        # Add net row
        waterfall_steps.append({
            "label": "NET MONTHLY IMPACT",
            "value": waterfall_data.net_monthly,
            "cumulative": waterfall_data.net_monthly,
            "type": "net",
            "source_agent": "synthesis",
            "note": None,
        })

    waterfall = {
        "title": "Where Does the Impact Land?",
        "subtitle": f"Monthly impact breakdown for {waterfall_data.household_profile}" if waterfall_data else "Monthly impact breakdown",
        "household_profile": waterfall_data.household_profile if waterfall_data else "",
        "steps": waterfall_steps,
        "net_monthly": waterfall_data.net_monthly if waterfall_data else 0,
        "net_annual": waterfall_data.net_annual if waterfall_data else 0,
        "pct_of_income": 0,
    }

    # --- impact_matrix ---
    impact_cells = []
    for hi in (agent_report.household_impacts or []):
        # Parse net_monthly string to number if possible
        try:
            net_val = float(hi.net_monthly.replace("$", "").replace(",", "").replace("+", "").strip()) if hi.net_monthly else 0
        except (ValueError, AttributeError):
            net_val = 0
        try:
            pct_val = float(hi.pct_of_income.replace("%", "").replace("+", "").strip()) if hi.pct_of_income else 0
        except (ValueError, AttributeError):
            pct_val = 0

        impact_cells.append({
            "income": hi.income_tier,
            "type": hi.household_type,
            "geography": hi.geography,
            "net_monthly": {"low": net_val * 0.8, "central": net_val, "high": net_val * 1.2},
            "net_annual": {"low": net_val * 0.8 * 12, "central": net_val * 12, "high": net_val * 1.2 * 12},
            "pct_of_income": {"low": pct_val * 0.8, "central": pct_val, "high": pct_val * 1.2},
            "confidence": (hi.confidence or "MEDIUM").upper(),
            "verdict": hi.verdict or "mixed",
            "dominant_inflow": hi.income_breakdown.get("primary", "") if hi.income_breakdown else "",
            "dominant_outflow": hi.cost_breakdown.get("primary", "") if hi.cost_breakdown else "",
            "note": f"Net: {hi.net_monthly}",
        })

    # Derive income tiers and geographies from cells
    income_tiers_seen = {}
    geo_seen = {}
    hh_types_seen = {}
    for cell in impact_cells:
        if cell["income"] and cell["income"] not in income_tiers_seen:
            income_tiers_seen[cell["income"]] = {"id": cell["income"], "label": cell["income"], "monthly": 0}
        if cell["geography"] and cell["geography"] not in geo_seen:
            geo_seen[cell["geography"]] = {"id": cell["geography"], "label": cell["geography"], "example": ""}
        if cell["type"] and cell["type"] not in hh_types_seen:
            hh_types_seen[cell["type"]] = {"id": cell["type"], "label": cell["type"]}

    impact_matrix = {
        "title": "Who Benefits Most? Who Benefits Least?",
        "subtitle": "Net monthly impact by household profile",
        "income_tiers": list(income_tiers_seen.values()),
        "geographies": list(geo_seen.values()),
        "household_types": list(hh_types_seen.values()),
        "cells": impact_cells,
    }

    # --- category_breakdown ---
    # Derived from sector report direct effects mapped to spending categories
    categories = []
    for report in state.sector_reports:
        for claim in report.direct_effects[:2]:
            categories.append({
                "name": claim.claim[:50],
                "icon": "📊",
                "pct_change": {"low": -1.0, "central": -0.5, "high": 0.0},
                "dollar_impact_monthly": {"low": -50, "central": -25, "high": 0},
                "budget_share_low_income": 0.1,
                "budget_share_middle_income": 0.08,
                "budget_share_high_income": 0.05,
                "pass_through_rate": claim.mechanism[:60] if claim.mechanism else "",
                "time_to_full_effect": "6-12 months",
                "source_agent": report.sector,
                "confidence": claim.confidence.value.upper(),
                "explanation": claim.mechanism,
            })

    category_breakdown = {
        "title": "Impact by Category",
        "subtitle": "How each dimension of the economy is affected",
        "categories": categories,
    }

    # --- timeline ---
    timeline_phases = []
    for th in (agent_report.timeline or []):
        timeline_phases.append({
            "label": th.label,
            "period_start": 0,
            "period_end": 12,
            "cumulative_net_monthly": {
                "low": th.cumulative_net_monthly_low,
                "central": th.cumulative_net_monthly_central,
                "high": th.cumulative_net_monthly_high,
            },
            "what_happens": th.dominant_effects,
            "mood": th.uncertainty or "uncertain",
            "dominant_driver": th.dominant_effects[0] if th.dominant_effects else "",
        })

    timeline = {
        "title": "When Will You Feel the Impact?",
        "subtitle": "Cumulative effect over time",
        "household_profile": waterfall_data.household_profile if waterfall_data else "",
        "phases": timeline_phases,
    }

    # --- winners_losers ---
    wl = agent_report.winners_losers
    winners_losers = {
        "title": "Winners and Losers",
        "winners": [
            {
                "profile": w.profile,
                "icon": "📈",
                "net_monthly_range": w.net_monthly,
                "pct_of_income_range": "",
                "why": w.why,
                "confidence": (w.confidence or "MEDIUM").upper(),
                "impact_quality": "",
                "depends_on": w.depends_on or "",
            }
            for w in (wl.winners if wl else [])
        ],
        "losers": [
            {
                "profile": l.profile,
                "icon": "📉",
                "net_monthly_range": l.net_monthly,
                "pct_of_income_range": "",
                "why": l.why,
                "confidence": (l.confidence or "MEDIUM").upper(),
                "impact_quality": "",
                "depends_on": l.depends_on or "",
            }
            for l in (wl.losers if wl else [])
        ],
        "mixed": [
            {
                "profile": m.profile,
                "icon": "↕️",
                "net_monthly_range": m.net_monthly,
                "pct_of_income_range": "",
                "why": m.why,
                "confidence": (m.confidence or "MEDIUM").upper(),
                "depends_on": m.depends_on or "",
            }
            for m in (wl.mixed if wl else [])
        ],
        "distributional_verdict": {
            "progressive_or_regressive": wl.distributional_verdict if wl else "",
            "explanation": "",
            "geographic_equity": "",
            "generational_equity": "",
        },
    }

    # --- geographic_impact ---
    geo_regions = []
    for gi in (agent_report.geographic_impacts or []):
        geo_regions.append({
            "id": gi.name.lower().replace(" ", "_"),
            "name": gi.name,
            "examples": "",
            "net_direction": gi.net_impact_direction,
            "color": "#66BB6A" if "positive" in (gi.net_impact_direction or "").lower() else "#FFA726",
            "rent_impact_severity": gi.rent_impact or "MEDIUM",
            "price_impact_severity": gi.price_impact or "MEDIUM",
            "net_monthly_range_median_hh": "",
            "explanation": gi.explanation,
            "key_factor": "",
        })

    geographic_impact = {
        "title": "Impact by Region",
        "regions": geo_regions,
    }

    # --- consistency_report ---
    audit = agent_report.consistency_audit
    consistency_adjustments = []
    if audit and audit.inconsistencies:
        for issue in audit.inconsistencies:
            consistency_adjustments.append({
                "variable": issue.variable,
                "original_source": ", ".join(issue.agents_involved),
                "original_value": next(iter(issue.values.values()), "") if issue.values else "",
                "issue": issue.resolution,
                "resolved_source": "Synthesis Agent",
                "resolved_value": issue.resolved_value,
                "impact_on_output": issue.impact_on_output,
                "severity": issue.severity or "MINOR",
            })

    consistency_report = {
        "title": "Cross-Agent Consistency Audit",
        "inconsistencies_found": len(consistency_adjustments),
        "adjustments": consistency_adjustments,
        "unresolved_gaps": audit.missing_inputs if audit else [],
    }

    # --- confidence_assessment ---
    confidence_breakdown = _count_confidences(state)
    total_claims = sum(confidence_breakdown.values())
    conf_components = []
    for sector_report in state.sector_reports:
        empirical = sum(1 for c in sector_report.direct_effects + sector_report.second_order_effects if c.confidence.value == "empirical")
        total = len(sector_report.direct_effects) + len(sector_report.second_order_effects)
        conf = "HIGH" if empirical > total * 0.5 else "MEDIUM" if empirical > 0 else "LOW"
        conf_components.append({
            "component": f"{sector_report.sector.title()} analysis",
            "confidence": conf,
            "reasoning": f"{empirical}/{total} claims backed by data",
        })

    confidence_assessment = {
        "overall": agent_report.overall_confidence or "MEDIUM",
        "by_component": conf_components,
        "weakest_link": agent_report.weakest_component or "",
        "what_would_change_conclusion": [],
    }

    # --- evidence_summary ---
    evidence_summary = {
        "title": "What the Research Says",
        "key_studies": [],
        "consensus": "",
        "major_gap": "",
    }

    # --- data_sources ---
    agents_and_calls = []
    for sr in state.sector_reports:
        agents_and_calls.append({
            "agent": sr.sector.title(),
            "tool_calls": len(sr.tool_calls_made),
            "key_data": [tc.tool for tc in sr.tool_calls_made[:5]],
            "phases_completed": 5 if sr.agent_mode == "agentic" else 1,
        })
    for ds in (agent_report.data_sources or []):
        agents_and_calls.append({
            "agent": ds.agent,
            "tool_calls": ds.tool_calls,
            "key_data": [],
            "phases_completed": 5,
        })

    data_sources = {
        "title": "Data Sources & Methodology",
        "agents_and_calls": agents_and_calls,
        "total_tool_calls": len(state.tool_calls),
        "total_unique_data_series": 0,
        "methodology_notes": [],
    }

    # --- narrative ---
    narrative_out = {
        "executive_summary": narrative.executive_summary if narrative else "",
        "for_low_income": "",
        "for_middle_income": "",
        "for_upper_income": "",
        "for_small_business": "",
        "biggest_uncertainty": narrative.biggest_uncertainty if narrative else "",
    }

    return {
        "meta": meta,
        "policy": policy,
        "headline": headline,
        "headline_metrics": headline_metrics,
        "waterfall": waterfall,
        "impact_matrix": impact_matrix,
        "category_breakdown": category_breakdown,
        "timeline": timeline,
        "winners_losers": winners_losers,
        "geographic_impact": geographic_impact,
        "consistency_report": consistency_report,
        "confidence_assessment": confidence_assessment,
        "evidence_summary": evidence_summary,
        "data_sources": data_sources,
        "narrative": narrative_out,
    }


# ---------------------------------------------------------------------------
# Simple fallback synthesis (single LLM call)
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM = """You are the SYNTHESIS AGENT in a multi-agent policy analysis system.
You receive 4 sector reports (labor, housing, consumer, business). Produce a unified analysis.

Respond with JSON:
{
  "summary": "2-3 paragraph personalized impact summary for the user",
  "key_findings": ["top 5-7 findings across all sectors"],
  "risk_factors": ["top 3-5 risks"],
  "opportunities": ["top 2-4 opportunities"],
  "agreed_findings": [
    {"finding": "...", "supporting_agents": ["labor", "consumer"], "confidence": "empirical|theoretical|speculative"}
  ],
  "disagreements": [
    {"topic": "...", "positions": {"labor": "...", "business": "..."}, "resolution": "..." }
  ],
  "sankey_flows": [
    {"source": "Policy", "target": "Mechanism", "value": 1, "label": "description"},
    {"source": "Mechanism", "target": "Sector Impact", "value": 1, "label": "description"}
  ]
}

The summary MUST be personalized to the user's context (role, concerns, situation).
Sankey flows should show: Policy → Mechanisms → Sector Impacts → User Outcomes."""


def _build_synthesis_context(state: PipelineState) -> str:
    """Build the context string for the synthesis LLM call."""
    parts = [
        f"Policy question: {state.query}",
        f"User context: {json.dumps(state.user_context)}",
        f"Policy classification: {json.dumps(state.policy_params)}",
        "",
        "=== SECTOR REPORTS ===",
    ]
    for report in state.sector_reports:
        parts.append(f"\n--- {report.sector.upper()} ---")
        for claim in report.direct_effects:
            parts.append(f"  [DIRECT] {claim.claim} (confidence: {claim.confidence.value})")
            parts.append(f"    mechanism: {claim.mechanism}")
        for claim in report.second_order_effects:
            parts.append(f"  [2ND ORDER] {claim.claim} (confidence: {claim.confidence.value})")
        if report.dissent:
            parts.append(f"  [DISSENT] {report.dissent}")

    return "\n".join(parts)[:8000]


async def _run_simple_synthesis(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Fallback: single LLM call synthesis, emitting new frontend schema."""
    import datetime

    async def _think(step_type: str, content: str, phase: int = 1) -> None:
        await emit({
            "type": "synthesis_thinking",
            "agent": "synthesis",
            "data": {"step_type": step_type, "content": content, "phase": str(phase)},
        })

    await _think("phase_start", "Synthesis (simple mode — LangGraph unavailable)")
    await emit({
        "type": "synthesis_phase",
        "agent": "synthesis",
        "data": {"phase": 1, "status": "running", "name": "Simple Synthesis"},
    })

    context = _build_synthesis_context(state)
    llm_summary = ""
    llm_findings = []
    llm_disagreements_raw = []

    await _think("reasoning", f"Aggregating {len(state.sector_reports)} sector reports...")

    try:
        await _think("tool_call", "llm_chat(synthesis prompt)")
        raw = await llm_chat(
            system_prompt=SYNTHESIS_SYSTEM,
            user_prompt=context,
            json_mode=True,
            temperature=0.2,
            max_tokens=4000,
        )
        if raw:
            parsed = parse_json_response(raw)
            llm_summary = parsed.get("summary", "")
            llm_findings = parsed.get("key_findings", [])
            llm_disagreements_raw = parsed.get("disagreements", [])
            await _think("tool_result", f"Generated summary with {len(llm_findings)} findings")
    except Exception as e:
        await _think("tool_result", f"LLM call failed: {str(e)[:100]}")
        pass

    if not llm_summary:
        llm_summary = f"Analysis of '{state.query}' across labor, housing, consumer, and business sectors."
        llm_findings = [c.claim for r in state.sector_reports for c in r.direct_effects[:2]]

    # Store internal pipeline model
    unified = UnifiedImpact(
        summary=llm_summary,
        key_findings=llm_findings,
        confidence_breakdown=_count_confidences(state),
    )
    sankey = _build_sankey_data(state, None)
    state.synthesis = PipelineSynthesisReport(
        policy_summary=PolicySummary(
            policy_name=state.policy_params.get("policy_name", "Policy"),
            parameters=state.policy_params.get("parameters", {}),
            affected_populations=state.policy_params.get("affected_populations", []),
        ),
        agreed_findings=[],
        disagreements=[],
        challenge_survival=[],
        unified_impact=unified,
        sankey_data=sankey,
        sector_reports=state.sector_reports,
        metadata={},
    )

    # Build the new frontend schema shape (same structure as _convert_agent_report)
    duration_s = int(sum(state.stage_times.values())) if state.stage_times else 0
    confidence_breakdown = _count_confidences(state)
    total_claims = sum(confidence_breakdown.values())

    # Derive category breakdown from sector claims
    categories = []
    for sr in state.sector_reports:
        for claim in sr.direct_effects[:2]:
            categories.append({
                "name": claim.claim[:50],
                "icon": "📊",
                "pct_change": {"low": -1.0, "central": -0.5, "high": 0.0},
                "dollar_impact_monthly": {"low": -50, "central": -25, "high": 0},
                "budget_share_low_income": 0.1,
                "budget_share_middle_income": 0.08,
                "budget_share_high_income": 0.05,
                "pass_through_rate": claim.mechanism[:60] if claim.mechanism else "",
                "time_to_full_effect": "6-12 months",
                "source_agent": sr.sector,
                "confidence": claim.confidence.value.upper(),
                "explanation": claim.mechanism,
            })

    # Confidence components
    conf_components = []
    for sr in state.sector_reports:
        empirical = sum(1 for c in sr.direct_effects + sr.second_order_effects if c.confidence.value == "empirical")
        total = len(sr.direct_effects) + len(sr.second_order_effects)
        conf = "HIGH" if empirical > total * 0.5 else "MEDIUM" if empirical > 0 else "LOW"
        conf_components.append({
            "component": f"{sr.sector.title()} analysis",
            "confidence": conf,
            "reasoning": f"{empirical}/{total} claims backed by data",
        })

    report_data = {
        "meta": {
            "version": "1.0",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "pipeline_duration_seconds": duration_s,
            "total_tool_calls": len(state.tool_calls),
            "agents_completed": ["policy_analyst"] + [r.sector for r in state.sector_reports],
            "agents_missing": [],
            "model_used": "fallback-simple",
            "query": state.query,
        },
        "policy": {
            "title": state.policy_params.get("policy_name", "Policy"),
            "one_liner": state.query,
            "type": state.policy_params.get("type", "other"),
            "geography": state.policy_params.get("scope", "Federal"),
            "effective_date": None,
            "current_baseline": "",
            "proposed_change": "",
            "estimated_annual_cost": "",
            "key_ambiguities": [],
            "working_assumptions": [],
        },
        "headline": {
            "verdict": llm_summary[:80] if llm_summary else "Analysis complete",
            "bottom_line": llm_summary,
            "confidence": "MEDIUM",
            "confidence_explanation": f"Based on {total_claims} claims across {len(state.sector_reports)} sectors",
        },
        "headline_metrics": [
            {"id": "claims", "label": "Claims Analyzed", "value": str(total_claims), "range": None, "unit": "count", "direction": "neutral", "confidence": "HIGH", "icon": "analytics", "context": "across 4 sectors"},
            {"id": "empirical", "label": "Evidence-Based", "value": str(confidence_breakdown.get("empirical", 0)), "range": None, "unit": "count", "direction": "positive", "confidence": "HIGH", "icon": "verified", "context": "with direct data"},
            {"id": "tools", "label": "Tool Calls", "value": str(len(state.tool_calls)), "range": None, "unit": "count", "direction": "neutral", "confidence": "HIGH", "icon": "build", "context": "data sources queried"},
        ],
        "waterfall": {
            "title": "Impact Breakdown",
            "subtitle": "Simple synthesis — detailed waterfall requires agentic mode",
            "household_profile": "",
            "steps": [],
            "net_monthly": 0,
            "net_annual": 0,
            "pct_of_income": 0,
        },
        "impact_matrix": {
            "title": "Household Impact Matrix",
            "subtitle": "Detailed matrix requires agentic synthesis",
            "income_tiers": [],
            "geographies": [],
            "household_types": [],
            "cells": [],
        },
        "category_breakdown": {
            "title": "Impact by Category",
            "subtitle": "Derived from sector agent claims",
            "categories": categories,
        },
        "timeline": {
            "title": "When Will You Feel the Impact?",
            "subtitle": "Timeline requires agentic synthesis",
            "household_profile": "",
            "phases": [],
        },
        "winners_losers": {
            "title": "Winners and Losers",
            "winners": [],
            "losers": [],
            "mixed": [],
            "distributional_verdict": {
                "progressive_or_regressive": "",
                "explanation": "",
                "geographic_equity": "",
                "generational_equity": "",
            },
        },
        "geographic_impact": {
            "title": "Impact by Region",
            "regions": [],
        },
        "consistency_report": {
            "title": "Cross-Agent Consistency Audit",
            "inconsistencies_found": 0,
            "adjustments": [],
            "unresolved_gaps": [],
        },
        "confidence_assessment": {
            "overall": "MEDIUM",
            "by_component": conf_components,
            "weakest_link": "",
            "what_would_change_conclusion": [],
        },
        "evidence_summary": {
            "title": "What the Research Says",
            "key_studies": [],
            "consensus": "",
            "major_gap": "",
        },
        "data_sources": {
            "title": "Data Sources & Methodology",
            "agents_and_calls": [
                {
                    "agent": sr.sector.title(),
                    "tool_calls": len(sr.tool_calls_made),
                    "key_data": [tc.tool for tc in sr.tool_calls_made[:5]],
                    "phases_completed": 5 if sr.agent_mode == "agentic" else 1,
                }
                for sr in state.sector_reports
            ],
            "total_tool_calls": len(state.tool_calls),
            "total_unique_data_series": 0,
            "methodology_notes": [],
        },
        "narrative": {
            "executive_summary": llm_summary,
            "for_low_income": "",
            "for_middle_income": "",
            "for_upper_income": "",
            "for_small_business": "",
            "biggest_uncertainty": "",
        },
    }

    await _think("phase_complete", "Synthesis complete — report assembled")
    await emit({
        "type": "synthesis_phase",
        "agent": "synthesis",
        "data": {"phase": 1, "status": "complete", "name": "Simple Synthesis"},
    })
    await emit({
        "type": "synthesis_complete",
        "agent": "synthesis",
        "data": {"report": report_data},
    })

    return state


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _build_impact_dashboard(state: PipelineState) -> list[dict]:
    """Build impact dashboard rows from sector direct effects."""
    impact_dashboard = []
    for report in state.sector_reports:
        for claim in report.direct_effects:
            effect_lower = (claim.effect + " " + claim.mechanism).lower()
            if any(w in effect_lower for w in ("increase", "rise", "grow", "higher", "boost", "gain")):
                direction = "increase"
            elif any(w in effect_lower for w in ("decrease", "decline", "fall", "lower", "reduce", "drop", "loss")):
                direction = "decline"
            elif any(w in effect_lower for w in ("distort", "misalloc", "perverse")):
                direction = "distortionary"
            else:
                direction = "mixed"

            if claim.confidence.value == "empirical":
                status = "works" if direction in ("increase", "decline") else "tradeoff"
            elif claim.confidence.value == "speculative":
                status = "doesnt_work"
            else:
                status = "tradeoff"

            impact_dashboard.append({
                "category": claim.claim[:80],
                "direction": direction,
                "magnitude": claim.effect[:60] if claim.effect else "TBD",
                "confidence": claim.confidence.value.upper(),
                "survived_challenge": "yes",
                "status": status,
                "sectors": [report.sector],
            })
    return impact_dashboard


def _build_sankey_data(state: PipelineState, llm_flows: list[dict] | None = None) -> SankeyData:
    """Build Sankey visualization data from pipeline state."""
    nodes: list[SankeyNode] = []
    links: list[SankeyLink] = []
    node_ids: set[str] = set()

    def add_node(id: str, label: str, category: str) -> None:
        if id not in node_ids:
            nodes.append(SankeyNode(id=id, label=label, category=category))
            node_ids.add(id)

    policy_name = state.policy_params.get("policy_name", "Policy Change")
    add_node("policy", policy_name, "policy")

    if llm_flows:
        for flow in llm_flows:
            src = flow.get("source", "").lower().replace(" ", "_")
            tgt = flow.get("target", "").lower().replace(" ", "_")
            if src and tgt:
                add_node(src, flow.get("source", src), "mechanism")
                add_node(tgt, flow.get("target", tgt), "outcome")
                links.append(SankeyLink(
                    source=src, target=tgt,
                    value=flow.get("value", 1),
                    label=flow.get("label", ""),
                ))
        return SankeyData(nodes=nodes, links=links)

    # Fallback: build from sector reports
    for report in state.sector_reports:
        sector_id = f"sector_{report.sector}"
        add_node(sector_id, report.sector.title(), "sector")
        links.append(SankeyLink(source="policy", target=sector_id, value=1))

        for i, claim in enumerate(report.direct_effects[:3]):
            effect_id = f"{report.sector}_effect_{i}"
            add_node(effect_id, claim.effect[:40], "outcome")
            links.append(SankeyLink(
                source=sector_id, target=effect_id,
                value=1, label=claim.mechanism[:60],
            ))

    return SankeyData(nodes=nodes, links=links)


def _count_confidences(state: PipelineState) -> dict[str, int]:
    """Count claims by confidence level across all sector reports."""
    counts: dict[str, int] = {"empirical": 0, "theoretical": 0, "speculative": 0}
    for report in state.sector_reports:
        for claim in report.direct_effects + report.second_order_effects + report.feedback_loops:
            counts[claim.confidence.value] = counts.get(claim.confidence.value, 0) + 1
    return counts

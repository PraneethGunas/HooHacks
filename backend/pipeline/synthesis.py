"""
Stage 4: Synthesis Agent — aggregates everything into the final report + Sankey data.

No external tool calls. Works purely on the outputs of previous stages.

===========================================================================
INTEGRATION GUIDE
===========================================================================
OWNER: Rudra (report quality) + Samank (Sankey data format)

The Sankey data structure must match what D3.js Sankey expects in the frontend.
Nodes have: id, label, category
Links have: source, target, value, label
===========================================================================
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from backend.models.pipeline import (
    SynthesisReport,
    PolicySummary,
    AgreedFinding,
    Disagreement,
    ChallengeOutcome,
    UnifiedImpact,
    SankeyData,
    SankeyNode,
    SankeyLink,
    ConfidenceLevel,
    RebuttalResponse,
)
from backend.pipeline.orchestrator import PipelineState
from backend.pipeline.llm import llm_chat, parse_json_response

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


SYNTHESIS_SYSTEM = """You are the SYNTHESIS AGENT in a multi-agent policy analysis system.
You receive sector reports, debate challenges, and rebuttals. Produce a unified analysis.

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

    if state.challenges:
        parts.append("\n=== DEBATE RESULTS ===")
        for rb in state.rebuttals:
            parts.append(
                f"  Challenge to {rb.challenge.target_agent}: {rb.challenge.target_claim.claim}"
                f" → Response: {rb.response.value}"
            )

    return "\n".join(parts)[:8000]


def _build_sankey_data(state: PipelineState, llm_flows: list[dict] | None = None) -> SankeyData:
    """Build Sankey visualization data from pipeline state."""
    nodes: list[SankeyNode] = []
    links: list[SankeyLink] = []
    node_ids: set[str] = set()

    def add_node(id: str, label: str, category: str) -> None:
        if id not in node_ids:
            nodes.append(SankeyNode(id=id, label=label, category=category))
            node_ids.add(id)

    # Policy node
    policy_name = state.policy_params.get("policy_name", "Policy Change")
    add_node("policy", policy_name, "policy")

    # If LLM provided flows, use them
    if llm_flows:
        for flow in llm_flows:
            src = flow.get("source", "").lower().replace(" ", "_")
            tgt = flow.get("target", "").lower().replace(" ", "_")
            if src and tgt:
                add_node(src, flow.get("source", src), "mechanism")
                add_node(tgt, flow.get("target", tgt), "outcome")
                links.append(SankeyLink(
                    source=src,
                    target=tgt,
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
                source=sector_id,
                target=effect_id,
                value=1,
                label=claim.mechanism[:60],
            ))

    return SankeyData(nodes=nodes, links=links)


async def run_synthesis(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 4: Synthesize all results into the final report."""
    await emit({
        "type": "agent_start",
        "agent": "synthesis",
        "data": {
            "sectors_analyzed": len(state.sector_reports),
            "challenges_issued": len(state.challenges),
        },
    })

    context = _build_synthesis_context(state)
    llm_flows = None
    unified = None

    try:
        raw = await llm_chat(
            system_prompt=SYNTHESIS_SYSTEM,
            user_prompt=context,
            json_mode=True,
            temperature=0.2,
            max_tokens=4000,
        )
        if raw:
            parsed = parse_json_response(raw)
            unified = UnifiedImpact(
                summary=parsed.get("summary", ""),
                key_findings=parsed.get("key_findings", []),
                risk_factors=parsed.get("risk_factors", []),
                opportunities=parsed.get("opportunities", []),
                confidence_breakdown=_count_confidences(state),
            )

            agreed = [
                AgreedFinding(
                    finding=f.get("finding", ""),
                    supporting_agents=f.get("supporting_agents", []),
                    confidence=ConfidenceLevel(f.get("confidence", "theoretical")),
                )
                for f in parsed.get("agreed_findings", [])
            ]

            disagreements = [
                Disagreement(
                    topic=d.get("topic", ""),
                    positions=d.get("positions", {}),
                    resolution=d.get("resolution"),
                )
                for d in parsed.get("disagreements", [])
            ]

            llm_flows = parsed.get("sankey_flows")
    except Exception:
        agreed = []
        disagreements = []

    if not unified:
        unified = UnifiedImpact(
            summary=f"Analysis of '{state.query}' across labor, housing, consumer, and business sectors.",
            key_findings=[
                c.claim
                for r in state.sector_reports
                for c in r.direct_effects[:2]
            ],
            risk_factors=[],
            opportunities=[],
            confidence_breakdown=_count_confidences(state),
        )
        agreed = []
        disagreements = []

    # Build challenge outcomes
    challenge_survival = []
    for rb in state.rebuttals:
        challenge_survival.append(ChallengeOutcome(
            challenge=rb.challenge,
            rebuttal=rb,
            survived=rb.response != RebuttalResponse.CONCEDE,
        ))

    sankey = _build_sankey_data(state, llm_flows)

    state.synthesis = SynthesisReport(
        policy_summary=PolicySummary(
            policy_name=state.policy_params.get("policy_name", "Policy"),
            parameters=state.policy_params.get("parameters", {}),
            affected_populations=state.policy_params.get("affected_populations", []),
        ),
        agreed_findings=agreed,
        disagreements=disagreements,
        challenge_survival=challenge_survival,
        unified_impact=unified,
        sankey_data=sankey,
        sector_reports=state.sector_reports,
        metadata={
            "session_id": state.session_id,
            "stage_times": state.stage_times,
            "total_tool_calls": len(state.tool_calls),
            "total_payments": len(state.payments),
            "total_sats_paid": sum(p.get("amount_sats", 0) for p in state.payments),
        },
    )

    # Build frontend-expected event shape with reshaped data
    # Uppercase all confidence levels in key claims
    all_direct_effects = []
    for report in state.sector_reports:
        for claim in report.direct_effects:
            claim_dict = claim.model_dump()
            claim_dict["confidence"] = claim.confidence.value.upper()
            all_direct_effects.append(claim_dict)

    # Generate headline stats from confidence breakdown
    confidence_breakdown = _count_confidences(state)
    total_claims = sum(confidence_breakdown.values())
    headline_stats = [
        {
            "label": "Claims Analyzed",
            "value": str(total_claims),
            "sub": "across 4 sectors",
        },
        {
            "label": "Evidence-Based",
            "value": str(confidence_breakdown.get("empirical", 0)),
            "sub": "with direct data",
        },
        {
            "label": "Challenges Survived",
            "value": str(sum(1 for cs in challenge_survival if cs.survived)),
            "sub": "after debate",
        },
    ]

    # Build reshaped policy_summary
    policy_summary = {
        "title": state.policy_params.get("policy_name", "Policy"),
        "scope": ", ".join(str(v) for v in state.policy_params.get("parameters", {}).values()),
        "affected_sectors": ["labor", "housing", "consumer", "business"],
    }

    # Build reshaped unified_impact
    unified_impact_reshaped = {
        "summary": unified.summary,
        "headline_stats": headline_stats,
        "key_claims": all_direct_effects,
    }

    # Build reshaped challenge_survival with proper shape
    challenge_survival_reshaped = [
        {
            "challenge": cs.challenge.model_dump(),
            "outcome": cs.rebuttal.response.value,
            "final_claim": cs.rebuttal.revised_claim.model_dump() if cs.rebuttal.revised_claim else cs.challenge.target_claim.model_dump(),
        }
        for cs in challenge_survival
    ]

    # Estimate total_llm_calls from stage count (rough estimate)
    total_llm_calls = 1 + 1 + 4 + 2 + 1  # classifier + analyst + 4 sectors + debate stages + synthesis

    # Compute total duration from stage_times
    duration_ms = int(sum(state.stage_times.values()) * 1000) if state.stage_times else 0

    # Build metadata with expected shape
    metadata = {
        "total_tool_calls": len(state.tool_calls),
        "total_llm_calls": total_llm_calls,
        "duration_ms": duration_ms,
        "lightning_payments": state.payments,
    }

    # Build impact_dashboard from sector direct_effects + challenge survival info
    survived_claims = set()
    for cs in challenge_survival:
        if cs.survived:
            survived_claims.add(cs.challenge.target_claim.claim)

    impact_dashboard = []
    for report in state.sector_reports:
        for claim in report.direct_effects:
            # Determine direction from mechanism/effect text
            effect_lower = (claim.effect + " " + claim.mechanism).lower()
            if any(w in effect_lower for w in ("increase", "rise", "grow", "higher", "boost", "gain")):
                direction = "increase"
            elif any(w in effect_lower for w in ("decrease", "decline", "fall", "lower", "reduce", "drop", "loss")):
                direction = "decline"
            elif any(w in effect_lower for w in ("distort", "misalloc", "perverse")):
                direction = "distortionary"
            else:
                direction = "mixed"

            # Determine status from confidence + direction
            if claim.confidence.value == "empirical":
                status = "works" if direction in ("increase", "decline") else "tradeoff"
            elif claim.confidence.value == "speculative":
                status = "doesnt_work"
            else:
                status = "tradeoff"

            survived = "yes" if claim.claim in survived_claims else ("no" if any(
                cs.challenge.target_claim.claim == claim.claim for cs in challenge_survival if not cs.survived
            ) else "partial")

            impact_dashboard.append({
                "category": claim.claim[:80],
                "direction": direction,
                "magnitude": claim.effect[:60] if claim.effect else "TBD",
                "confidence": claim.confidence.value.upper(),
                "survived_challenge": survived,
                "status": status,
                "sectors": [report.sector],
            })

    # Build agreed_findings with frontend-expected shape (claim + agreeing_agents)
    agreed_findings_reshaped = [
        {
            "claim": {
                "claim": a.finding,
                "cause": "",
                "effect": "",
                "mechanism": "",
                "confidence": a.confidence.value.upper(),
                "evidence": [],
                "assumptions": [],
                "sensitivity": None,
            },
            "agreeing_agents": a.supporting_agents,
        }
        for a in agreed
    ]

    # Build final report with frontend-expected shape
    report_data = {
        "policy_summary": policy_summary,
        "unified_impact": unified_impact_reshaped,
        "impact_dashboard": impact_dashboard,
        "sankey_data": sankey.model_dump(),
        "disagreements": [d.model_dump() for d in disagreements],
        "agreed_findings": agreed_findings_reshaped,
        "challenge_survival": challenge_survival_reshaped,
        "metadata": metadata,
    }

    await emit({
        "type": "synthesis_complete",
        "agent": "synthesis",
        "data": {
            "report": report_data,
        },
    })

    return state


def _count_confidences(state: PipelineState) -> dict[str, int]:
    """Count claims by confidence level across all sector reports."""
    counts: dict[str, int] = {"empirical": 0, "theoretical": 0, "speculative": 0}
    for report in state.sector_reports:
        for claim in report.direct_effects + report.second_order_effects + report.feedback_loops:
            counts[claim.confidence.value] = counts.get(claim.confidence.value, 0) + 1
    return counts

"""
Stage 3: Debate Agent — adversarially challenges the weakest claims.

Reads all 4 SectorReports, identifies the most vulnerable claims, and issues
formal AgentChallenges. Then each challenged agent produces an AgentRebuttal
(concede, defend, or revise).

===========================================================================
INTEGRATION GUIDE
===========================================================================
OWNER: Rudra — enhance with LangGraph multi-turn debate if time permits.

Currently: single-pass LLM call generates 3-5 challenges, then a second
LLM call generates rebuttals. With LangGraph, this becomes a multi-turn
conversation between the debate agent and the sector agents.
===========================================================================
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from backend.models.pipeline import (
    AgentChallenge,
    AgentRebuttal,
    CausalClaim,
    ChallengeType,
    RebuttalResponse,
    ConfidenceLevel,
)
from backend.pipeline.orchestrator import PipelineState
from backend.pipeline.llm import llm_chat, parse_json_response

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


DEBATE_SYSTEM = """You are the DEBATE AGENT in a multi-agent policy analysis system.
Your role is adversarial: find the weakest claims across all sector reports and challenge them.

You receive 4 sector reports (labor, housing, consumer, business), each containing
CausalClaims with confidence levels and evidence.

Produce 3-5 challenges as JSON array:
[
  {
    "target_agent": "labor|housing|consumer|business",
    "target_claim": "<the exact claim text being challenged>",
    "challenge_type": "assumption_conflict|confidence_inflation|missing_mechanism|blind_spot",
    "counter_evidence": ["evidence that undermines the claim"],
    "proposed_revision": "suggested fix or null"
  }
]

Challenge types:
- assumption_conflict: Two agents made contradictory assumptions
- confidence_inflation: Claim marked EMPIRICAL but evidence is weak
- missing_mechanism: Claim doesn't adequately explain HOW
- blind_spot: Important effect that no agent mentioned

Focus on claims where getting it wrong has the highest stakes for the user."""


REBUTTAL_SYSTEM = """You are a sector analyst responding to a formal challenge from the debate agent.
For each challenge, you must respond with one of:
- "concede": The challenge is valid, withdraw the claim
- "defend": The challenge is wrong, explain why with new evidence
- "revise": The challenge has merit, but the claim can be salvaged with modifications

Respond as JSON array:
[
  {
    "response": "concede|defend|revise",
    "explanation": "why you chose this response",
    "revised_claim": "the revised claim text if response is 'revise', else null",
    "new_evidence": ["any new supporting evidence"]
  }
]"""


def _build_reports_summary(state: PipelineState) -> str:
    """Serialize sector reports for the debate agent's context."""
    summaries = []
    for report in state.sector_reports:
        claims = []
        for claim in report.direct_effects + report.second_order_effects:
            claims.append({
                "claim": claim.claim,
                "mechanism": claim.mechanism,
                "confidence": claim.confidence.value,
                "evidence": claim.evidence[:3],
                "assumptions": claim.assumptions,
            })
        summaries.append({
            "sector": report.sector,
            "claims": claims,
            "dissent": report.dissent,
        })
    return json.dumps(summaries, indent=2)[:6000]


def _find_claim_by_text(state: PipelineState, agent: str, claim_text: str) -> CausalClaim:
    """Find a CausalClaim by matching its text."""
    for report in state.sector_reports:
        if report.sector == agent:
            for claim in report.direct_effects + report.second_order_effects + report.feedback_loops:
                if claim_text.lower() in claim.claim.lower() or claim.claim.lower() in claim_text.lower():
                    return claim
    # Fallback: return a minimal claim
    return CausalClaim(
        claim=claim_text,
        cause="unknown",
        effect="unknown",
        mechanism="unspecified",
        confidence=ConfidenceLevel.SPECULATIVE,
    )


async def run_debate(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 3: Debate agent challenges weakest claims, sector agents respond."""
    await emit({
        "type": "agent_start",
        "agent": "debate",
        "data": {"analyzing_sectors": [r.sector for r in state.sector_reports]},
    })

    reports_summary = _build_reports_summary(state)

    # --- Generate Challenges ---
    challenges: list[AgentChallenge] = []
    try:
        raw = await llm_chat(
            system_prompt=DEBATE_SYSTEM,
            user_prompt=(
                f"Policy question: {state.query}\n\n"
                f"Sector reports:\n{reports_summary}"
            ),
            json_mode=True,
            temperature=0.4,
            max_tokens=3000,
        )
        if raw:
            parsed = parse_json_response(raw)
            if not isinstance(parsed, list):
                parsed = parsed.get("challenges", [])
            for ch in parsed[:5]:  # cap at 5 challenges
                target_claim = _find_claim_by_text(
                    state,
                    ch.get("target_agent", ""),
                    ch.get("target_claim", ""),
                )
                challenges.append(AgentChallenge(
                    target_agent=ch.get("target_agent", "unknown"),
                    target_claim=target_claim,
                    challenge_type=ChallengeType(
                        ch.get("challenge_type", "missing_mechanism")
                    ),
                    counter_evidence=ch.get("counter_evidence", []),
                    proposed_revision=ch.get("proposed_revision"),
                ))
    except Exception:
        # If debate fails, generate a minimal challenge
        if state.sector_reports:
            report = state.sector_reports[0]
            if report.direct_effects:
                challenges.append(AgentChallenge(
                    target_agent=report.sector,
                    target_claim=report.direct_effects[0],
                    challenge_type=ChallengeType.CONFIDENCE_INFLATION,
                    counter_evidence=["Debate agent unavailable — auto-generated challenge"],
                ))

    state.challenges = challenges

    # Emit challenge events
    for ch in challenges:
        await emit({
            "type": "debate_challenge",
            "agent": "debate",
            "data": {
                "target_agent": ch.target_agent,
                "target_claim": ch.target_claim.claim,
                "challenge_type": ch.challenge_type.value,
                "counter_evidence": ch.counter_evidence,
            },
        })

    # --- Generate Rebuttals ---
    rebuttals: list[AgentRebuttal] = []
    try:
        challenges_json = json.dumps([
            {
                "target_agent": ch.target_agent,
                "target_claim": ch.target_claim.claim,
                "challenge_type": ch.challenge_type.value,
                "counter_evidence": ch.counter_evidence,
                "proposed_revision": ch.proposed_revision,
            }
            for ch in challenges
        ])

        raw = await llm_chat(
            system_prompt=REBUTTAL_SYSTEM,
            user_prompt=(
                f"You are the challenged sector analysts. Respond to each challenge:\n\n"
                f"Challenges:\n{challenges_json}\n\n"
                f"Original sector data:\n{reports_summary}"
            ),
            json_mode=True,
            temperature=0.3,
            max_tokens=2000,
        )
        if raw:
            parsed = parse_json_response(raw)
            if not isinstance(parsed, list):
                parsed = parsed.get("rebuttals", [])
            for i, rb in enumerate(parsed):
                if i >= len(challenges):
                    break
                ch = challenges[i]
                response = RebuttalResponse(rb.get("response", "defend"))
                revised = None
                if response == RebuttalResponse.REVISE and rb.get("revised_claim"):
                    revised = CausalClaim(
                        claim=rb["revised_claim"],
                        cause=ch.target_claim.cause,
                        effect=ch.target_claim.effect,
                        mechanism=ch.target_claim.mechanism,
                        confidence=ch.target_claim.confidence,
                        evidence=ch.target_claim.evidence + rb.get("new_evidence", []),
                        assumptions=ch.target_claim.assumptions,
                    )
                rebuttals.append(AgentRebuttal(
                    original_claim=ch.target_claim,
                    challenge=ch,
                    response=response,
                    revised_claim=revised,
                    new_evidence=rb.get("new_evidence", []),
                ))
    except Exception:
        # Auto-defend if rebuttal generation fails
        for ch in challenges:
            rebuttals.append(AgentRebuttal(
                original_claim=ch.target_claim,
                challenge=ch,
                response=RebuttalResponse.DEFEND,
                new_evidence=["Rebuttal generation failed — claim auto-defended"],
            ))

    state.rebuttals = rebuttals

    # Emit revision events
    for rb in rebuttals:
        await emit({
            "type": "revision_complete",
            "agent": rb.challenge.target_agent,
            "data": {
                "original_claim": rb.original_claim.claim,
                "challenge_type": rb.challenge.challenge_type.value,
                "response": rb.response.value,
                "revised_claim": rb.revised_claim.claim if rb.revised_claim else None,
            },
        })

    return state

"""
Pipeline data models — the structured epistemic objects that flow between agents.

These are the FIXED data schemas from CLAUDE.md. Agents reason over each other's
structured claims, not raw text.

Every CausalClaim must have a mechanism (HOW cause → effect). Every claim has
a confidence level that determines the evidence bar.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, Enum):
    """
    Confidence levels with increasing evidence requirements.
    EMPIRICAL: Backed by retrieved data (FRED/BLS/Census or peer-reviewed studies)
    THEORETICAL: Follows from economic models, must cite model + assumptions
    SPECULATIVE: Agent reasoning, flagged as uncertain, cannot appear in final report uncaveated
    """
    EMPIRICAL = "empirical"
    THEORETICAL = "theoretical"
    SPECULATIVE = "speculative"


class ChallengeType(str, Enum):
    ASSUMPTION_CONFLICT = "assumption_conflict"
    CONFIDENCE_INFLATION = "confidence_inflation"
    MISSING_MECHANISM = "missing_mechanism"
    BLIND_SPOT = "blind_spot"


class RebuttalResponse(str, Enum):
    CONCEDE = "concede"
    DEFEND = "defend"
    REVISE = "revise"


# ---------------------------------------------------------------------------
# Core Epistemic Objects
# ---------------------------------------------------------------------------

class ToolCallRecord(BaseModel):
    """Record of a tool invocation made by an agent."""
    tool: str
    query: str | dict[str, Any] = ""
    success: bool = True
    summary: str = ""


class CausalClaim(BaseModel):
    """
    The fundamental unit of agent reasoning.
    Agents CANNOT say "X leads to Y" without specifying the mechanism.
    """
    claim: str
    cause: str
    effect: str
    mechanism: str  # HOW cause → effect (MANDATORY)
    confidence: ConfidenceLevel
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    sensitivity: str | None = None  # "If X changes, this conclusion breaks"


class SectorReport(BaseModel):
    """Output from a sector agent (Labor, Housing, Consumer, Business)."""
    sector: str
    direct_effects: list[CausalClaim] = Field(default_factory=list)
    second_order_effects: list[CausalClaim] = Field(default_factory=list)
    feedback_loops: list[CausalClaim] = Field(default_factory=list)
    cross_sector_dependencies: list[str] = Field(default_factory=list)
    dissent: str | None = None
    tool_calls_made: list[ToolCallRecord] = Field(default_factory=list)
    agent_mode: str = Field(default="single_shot", description="'agentic' (LangGraph multi-phase) or 'single_shot' (one-pass LLM)")


class AgentChallenge(BaseModel):
    """A challenge from the Debate Agent targeting a specific claim."""
    target_agent: str
    target_claim: CausalClaim
    challenge_type: ChallengeType
    counter_evidence: list[str] = Field(default_factory=list)
    proposed_revision: str | None = None


class AgentRebuttal(BaseModel):
    """A sector agent's response to a debate challenge."""
    original_claim: CausalClaim
    challenge: AgentChallenge
    response: RebuttalResponse
    revised_claim: CausalClaim | None = None
    new_evidence: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Synthesis Report
# ---------------------------------------------------------------------------

class PolicySummary(BaseModel):
    policy_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    affected_populations: list[str] = Field(default_factory=list)


class AgreedFinding(BaseModel):
    finding: str
    supporting_agents: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.THEORETICAL
    evidence_count: int = 0


class Disagreement(BaseModel):
    topic: str
    positions: dict[str, str] = Field(default_factory=dict)  # agent → position
    resolution: str | None = None


class ChallengeOutcome(BaseModel):
    challenge: AgentChallenge
    rebuttal: AgentRebuttal
    survived: bool  # True if the original claim was defended/revised, False if conceded


class UnifiedImpact(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    confidence_breakdown: dict[str, int] = Field(default_factory=dict)  # level → count


class SankeyNode(BaseModel):
    id: str
    label: str
    category: str = ""  # "policy", "mechanism", "sector", "outcome"


class SankeyLink(BaseModel):
    source: str  # node id
    target: str  # node id
    value: float = 1.0
    label: str = ""


class SankeyData(BaseModel):
    nodes: list[SankeyNode] = Field(default_factory=list)
    links: list[SankeyLink] = Field(default_factory=list)


class SynthesisReport(BaseModel):
    """Final output of the full pipeline."""
    policy_summary: PolicySummary
    agreed_findings: list[AgreedFinding] = Field(default_factory=list)
    disagreements: list[Disagreement] = Field(default_factory=list)
    challenge_survival: list[ChallengeOutcome] = Field(default_factory=list)
    unified_impact: UnifiedImpact
    sankey_data: SankeyData
    sector_reports: list[SectorReport] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

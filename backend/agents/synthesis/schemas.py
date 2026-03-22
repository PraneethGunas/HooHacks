from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

from backend.agents.schemas import AnalystBriefing, ToolCallRecord
from backend.agents.housing.schemas import HousingReport
from backend.agents.consumer.schemas import ConsumerReport


# ---------------------------------------------------------------------------
# Phase 1: Input Validation + Consistency Audit
# ---------------------------------------------------------------------------

class AgentInventory(BaseModel):
    agent_name: str = ""
    status: str = ""  # "RECEIVED" | "MISSING" | "PARTIAL"
    confidence: str = ""
    key_findings_count: int = 0
    data_gaps: list[str] = Field(default_factory=list)


class ConsistencyIssue(BaseModel):
    variable: str = ""
    agents_involved: list[str] = Field(default_factory=list)
    values: dict[str, str] = Field(default_factory=dict)
    severity: str = ""  # "MATERIAL" | "MINOR"
    resolution: str = ""
    resolved_value: str = ""
    impact_on_output: str = ""


class ConsistencyAuditOutput(BaseModel):
    input_inventory: list[AgentInventory] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    inconsistencies: list[ConsistencyIssue] = Field(default_factory=list)
    resolution_summary: str = ""


# ---------------------------------------------------------------------------
# Phase 2: Net Household Impact
# ---------------------------------------------------------------------------

class HouseholdImpact(BaseModel):
    income_tier: str = ""
    household_type: str = ""
    geography: str = ""
    # Income side
    total_income_change: str = ""
    income_breakdown: dict[str, str] = Field(default_factory=dict)
    # Cost side
    total_cost_change: str = ""
    cost_breakdown: dict[str, str] = Field(default_factory=dict)
    # Net
    net_monthly: str = ""
    net_annual: str = ""
    pct_of_income: str = ""
    verdict: str = ""  # "better_off" | "worse_off" | "roughly_neutral"
    confidence: str = ""


class WaterfallStep(BaseModel):
    label: str = ""
    value: float = 0.0
    type: str = ""  # "inflow" | "outflow" | "net"


class WaterfallData(BaseModel):
    household_profile: str = ""
    steps: list[WaterfallStep] = Field(default_factory=list)
    net_monthly: float = 0.0
    net_annual: float = 0.0


class NetImpactOutput(BaseModel):
    household_impacts: list[HouseholdImpact] = Field(default_factory=list)
    waterfall: WaterfallData | None = None
    computation_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 3: Winners/Losers + Confidence
# ---------------------------------------------------------------------------

class WinnerLoserProfile(BaseModel):
    profile: str = ""
    net_monthly: str = ""
    why: str = ""
    confidence: str = ""
    depends_on: str = ""


class WinnersLosersOutput(BaseModel):
    winners: list[WinnerLoserProfile] = Field(default_factory=list)
    losers: list[WinnerLoserProfile] = Field(default_factory=list)
    mixed: list[WinnerLoserProfile] = Field(default_factory=list)
    distributional_verdict: str = ""
    overall_confidence: str = ""
    weakest_component: str = ""
    what_could_change: str = ""


# ---------------------------------------------------------------------------
# Phase 4: Timeline + Narrative
# ---------------------------------------------------------------------------

class TimelineHorizon(BaseModel):
    label: str = ""
    cumulative_net_monthly_low: float = 0.0
    cumulative_net_monthly_central: float = 0.0
    cumulative_net_monthly_high: float = 0.0
    dominant_effects: list[str] = Field(default_factory=list)
    uncertainty: str = ""


class NarrativeOutput(BaseModel):
    executive_summary: str = ""
    bottom_line: str = ""
    key_findings: list[str] = Field(default_factory=list)
    biggest_uncertainty: str = ""
    timeline: list[TimelineHorizon] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 5: Final Analytics Payload (SynthesisReport)
# ---------------------------------------------------------------------------

class HeadlineMetric(BaseModel):
    label: str = ""
    value: str = ""
    direction: str = ""  # "positive" | "negative" | "neutral"
    confidence: str = ""
    context: str = ""


class GeographicImpact(BaseModel):
    name: str = ""
    net_impact_direction: str = ""
    rent_impact: str = ""
    price_impact: str = ""
    explanation: str = ""


class DataSourceSummary(BaseModel):
    agent: str = ""
    tool_calls: int = 0


# ---------------------------------------------------------------------------
# Reasoning Chain — shows HOW the system arrived at its conclusions
# ---------------------------------------------------------------------------

class PolicyClassification(BaseModel):
    """Phase 0 classification that drove the entire analysis."""
    policy_type: str = ""               # LABOR_COST, REGULATORY_COST, etc.
    income_effect_exists: bool | None = None
    income_effect_explanation: str = ""
    analysis_mode: str = ""             # BILATERAL or PURE_COST
    reasoning: str = ""                 # Why this classification


class ChannelDecision(BaseModel):
    """A single transmission channel and whether it was activated or gated out."""
    name: str = ""
    status: str = ""                    # ACTIVE, SECONDARY, NULL
    reason: str = ""                    # Why this status
    magnitude: str = ""                 # Central estimate if ACTIVE
    confidence: str = ""
    downstream_instruction: str = ""    # What sector agents were told


class AgentFrameworkTrace(BaseModel):
    """How a single agent applied its domain-specific framework."""
    agent_name: str = ""
    framework_name: str = ""            # e.g., "Stock-Flow-Price", "Price Transmission Pipeline"
    mode: str = ""                      # e.g., "Mode B (Pure Cost)", "Full Analysis"
    pathways_activated: list[str] = Field(default_factory=list)
    pathways_skipped: list[str] = Field(default_factory=list)
    skip_reasons: list[str] = Field(default_factory=list)
    key_finding: str = ""              # One-sentence headline from this agent
    key_data_used: list[str] = Field(default_factory=list)    # e.g., "FRED:HOUST (1,487K starts)"
    key_elasticities: list[str] = Field(default_factory=list)  # e.g., "Rent elasticity: 0.5 (tight market)"
    materiality_check: str = ""         # e.g., "Impact >$50/mo — full analysis" or "Impact <$8/mo — negligible"
    tool_calls: int = 0
    phases_completed: int = 0


class ReasoningChain(BaseModel):
    """The complete reasoning chain — shows HOW the system arrived at its conclusions."""
    # Step 1: Classification
    classification: PolicyClassification | None = None
    # Step 2: Channel map
    channel_decisions: list[ChannelDecision] = Field(default_factory=list)
    active_channels: int = 0
    null_channels: int = 0
    # Step 3: Per-agent framework trace
    agent_traces: list[AgentFrameworkTrace] = Field(default_factory=list)
    # Step 4: Consistency resolutions
    consistency_resolutions: list[str] = Field(default_factory=list)
    phantom_channels_detected: list[str] = Field(default_factory=list)
    # Step 5: The logic chain in plain English
    reasoning_summary: str = ""         # 3-4 sentences: "The analyst classified this as X → told agents Y → housing found Z → consumer found W → synthesis computed Q"


class DataProvenance(BaseModel):
    """Traces a specific finding back to its source data."""
    finding: str = ""                   # e.g., "+$127/month rent increase in tight markets"
    data_sources: list[str] = Field(default_factory=list)  # e.g., ["FRED:MORTGAGE30US (6.9%)", "Census ACS B25064 ($1,295 median rent)"]
    methodology: str = ""               # e.g., "Income elasticity 0.5 × 10% income shock × $1,295 baseline"
    computed_by: str = ""               # e.g., "Housing Agent Phase 3 via code_execute"
    confidence: str = ""


class SynthesisReport(BaseModel):
    """The final output — unified analysis payload for the frontend.

    Three layers:
    - Layer 1 (headline): Bottom line numbers for quick consumption
    - Layer 2 (reasoning): HOW the system arrived at these numbers
    - Layer 3 (deep dive): Per-agent framework traces and data provenance
    """
    # ── LAYER 1: HEADLINE ──────────────────────────────────────────
    policy_title: str = ""
    policy_one_liner: str = ""

    headline_metrics: list[HeadlineMetric] = Field(default_factory=list)
    household_impacts: list[HouseholdImpact] = Field(default_factory=list)
    waterfall: WaterfallData | None = None
    winners_losers: WinnersLosersOutput | None = None
    geographic_impacts: list[GeographicImpact] = Field(default_factory=list)
    timeline: list[TimelineHorizon] = Field(default_factory=list)

    overall_confidence: str = ""
    strongest_component: str = ""
    weakest_component: str = ""

    narrative: NarrativeOutput | None = None

    # ── LAYER 2: REASONING CHAIN ───────────────────────────────────
    reasoning_chain: ReasoningChain | None = None

    # ── LAYER 3: DEEP DIVE ─────────────────────────────────────────
    data_provenance: list[DataProvenance] = Field(default_factory=list)
    data_sources: list[DataSourceSummary] = Field(default_factory=list)
    consistency_audit: ConsistencyAuditOutput | None = None

    # ── META ───────────────────────────────────────────────────────
    analysis_mode: str = ""             # BILATERAL or PURE_COST
    total_tool_calls: int = 0
    total_phases_completed: int = 0
    agents_that_ran: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------

class SynthesisState(TypedDict, total=False):
    # Inputs from upstream agents
    analyst_briefing: AnalystBriefing
    housing_report: HousingReport | None
    consumer_report: ConsumerReport | None
    policy_query: str
    # Phase tracking
    current_phase: int
    # Phase outputs
    phase_1_output: ConsistencyAuditOutput | None
    phase_2_output: NetImpactOutput | None
    phase_3_output: WinnersLosersOutput | None
    phase_4_output: NarrativeOutput | None
    phase_5_output: SynthesisReport | None
    # Summaries
    phase_1_summary: str | None
    phase_2_summary: str | None
    phase_3_summary: str | None
    tool_call_log: list[ToolCallRecord]

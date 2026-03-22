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


class SynthesisReport(BaseModel):
    """The final output — unified analysis payload for the frontend."""
    # Policy context
    policy_title: str = ""
    policy_one_liner: str = ""

    # Headline metrics
    headline_metrics: list[HeadlineMetric] = Field(default_factory=list)

    # Household impact matrix
    household_impacts: list[HouseholdImpact] = Field(default_factory=list)

    # Waterfall chart data
    waterfall: WaterfallData | None = None

    # Winners and losers
    winners_losers: WinnersLosersOutput | None = None

    # Geographic impact
    geographic_impacts: list[GeographicImpact] = Field(default_factory=list)

    # Timeline
    timeline: list[TimelineHorizon] = Field(default_factory=list)

    # Consistency report
    consistency_audit: ConsistencyAuditOutput | None = None

    # Confidence
    overall_confidence: str = ""
    strongest_component: str = ""
    weakest_component: str = ""

    # Narrative
    narrative: NarrativeOutput | None = None

    # Data sources
    data_sources: list[DataSourceSummary] = Field(default_factory=list)


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

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

from backend.agents.schemas import AnalystBriefing, ToolCallRecord


# ---------------------------------------------------------------------------
# Phase 1: Transmission Pathway Identification
# ---------------------------------------------------------------------------

class TransmissionPathway(BaseModel):
    pathway_id: str = ""
    name: str = ""
    mechanism: str = ""
    relevance: str = "NONE"
    direction: str = ""
    confidence: str = "THEORETICAL"
    notes: str = ""


class PathwayIdentificationOutput(BaseModel):
    pathways: list[TransmissionPathway] = Field(default_factory=list)
    primary_pathways: list[str] = Field(default_factory=list)
    housing_relevance_summary: str = ""


# ---------------------------------------------------------------------------
# Phase 2: Housing Market Baseline
# ---------------------------------------------------------------------------

class HousingBaselineMetric(BaseModel):
    metric_name: str = ""
    value: str = ""
    source: str = ""
    date: str = ""
    geography: str = ""
    trend: str = ""


class SubMarketAssessment(BaseModel):
    name: str = ""
    tightness: str = ""
    vacancy_rate: str = ""
    median_rent: str = ""
    median_home_price: str = ""
    price_trend: str = ""
    notes: str = ""


class HousingBaselineOutput(BaseModel):
    supply_metrics: list[HousingBaselineMetric] = Field(default_factory=list)
    demand_metrics: list[HousingBaselineMetric] = Field(default_factory=list)
    price_metrics: list[HousingBaselineMetric] = Field(default_factory=list)
    sub_markets: list[SubMarketAssessment] = Field(default_factory=list)
    overall_tightness: str = ""
    data_gaps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 3: Magnitude Estimation
# ---------------------------------------------------------------------------

class MagnitudeEstimate(BaseModel):
    pathway_id: str = ""
    metric: str = ""
    low_estimate: str = ""
    central_estimate: str = ""
    high_estimate: str = ""
    methodology: str = ""
    time_horizon: str = ""
    geography: str = ""
    assumptions: list[str] = Field(default_factory=list)


class MagnitudeEstimationOutput(BaseModel):
    estimates: list[MagnitudeEstimate] = Field(default_factory=list)
    key_elasticities_used: dict[str, str] = Field(default_factory=dict)
    nominal_vs_real_analysis: str = ""
    computation_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 4: Distributional + Temporal
# ---------------------------------------------------------------------------

class IncomeTierImpact(BaseModel):
    income_level: str = ""
    tenure: str = ""
    monthly_housing_cost_change: str = ""
    housing_cost_share_before: str = ""
    housing_cost_share_after: str = ""
    crosses_burden_threshold: bool = False
    net_income_effect: str = ""


class TemporalEffect(BaseModel):
    horizon: str = ""
    description: str = ""
    dominant_channel: str = ""
    magnitude: str = ""
    uncertainty: str = "MEDIUM"


class DistributionalTemporalOutput(BaseModel):
    by_tenure: dict[str, list[str]] = Field(default_factory=dict)
    by_income: list[IncomeTierImpact] = Field(default_factory=list)
    by_geography: dict[str, list[str]] = Field(default_factory=dict)
    by_household_type: dict[str, list[str]] = Field(default_factory=dict)
    temporal_sequence: list[TemporalEffect] = Field(default_factory=list)
    computation_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 5: Affordability Scorecard + Housing Report
# ---------------------------------------------------------------------------

class SubMarketScorecard(BaseModel):
    region_name: str = ""
    current_median_rent: str = ""
    current_median_home_price: str = ""
    current_monthly_mortgage: str = ""
    current_median_income: str = ""
    current_rent_to_income: str = ""
    current_cost_burden_rate: str = ""
    rent_change: str = ""
    home_price_change: str = ""
    mortgage_payment_change: str = ""
    net_affordability_shift: str = ""
    impact_at_35k: str = ""
    impact_at_55k: str = ""
    impact_at_85k: str = ""
    confidence: str = ""
    primary_driver: str = ""
    timeline: str = ""


class AffordabilityScorecard(BaseModel):
    sub_markets: list[SubMarketScorecard] = Field(default_factory=list)
    methodology_notes: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class CausalClaimSimple(BaseModel):
    """Simplified CausalClaim for housing report output."""
    claim: str = ""
    cause: str = ""
    effect: str = ""
    mechanism: str = ""
    confidence: str = "THEORETICAL"
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    sensitivity: str | None = None


class HousingReport(BaseModel):
    """Housing sector report — the final output."""
    sector: str = "housing"
    direct_effects: list[CausalClaimSimple] = Field(default_factory=list)
    second_order_effects: list[CausalClaimSimple] = Field(default_factory=list)
    feedback_loops: list[CausalClaimSimple] = Field(default_factory=list)
    cross_sector_dependencies: list[str] = Field(default_factory=list)
    dissent: str | None = None

    # Housing-specific phase outputs
    pathway_analysis: PathwayIdentificationOutput | None = None
    housing_baseline: HousingBaselineOutput | None = None
    magnitude_estimates: MagnitudeEstimationOutput | None = None
    distributional_temporal: DistributionalTemporalOutput | None = None
    affordability_scorecard: AffordabilityScorecard | None = None


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------

class HousingState(TypedDict, total=False):
    analyst_briefing: AnalystBriefing
    policy_query: str
    current_phase: int
    phase_1_output: PathwayIdentificationOutput | None
    phase_2_output: HousingBaselineOutput | None
    phase_3_output: MagnitudeEstimationOutput | None
    phase_4_output: DistributionalTemporalOutput | None
    phase_5_output: HousingReport | None
    # LLM-generated summaries to keep prompts compact
    phase_2_summary: str | None
    phase_3_summary: str | None
    phase_4_summary: str | None
    tool_call_log: list[ToolCallRecord]

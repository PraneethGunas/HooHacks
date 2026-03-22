from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

from backend.agents.schemas import AnalystBriefing, ToolCallRecord


# ---------------------------------------------------------------------------
# Phase 1: Price Shock Entry Point Identification
# ---------------------------------------------------------------------------

class PriceShockEntry(BaseModel):
    entry_type: str = ""       # "labor_cost" | "input_material" | "tax_fee" | "regulatory"
    name: str = ""
    mechanism: str = ""
    affected_industries: list[str] = Field(default_factory=list)
    labor_cost_share: str = ""  # e.g., "30% for restaurants, 5% for manufacturing"
    initial_magnitude: str = ""
    relevance: str = "NONE"     # HIGH | MEDIUM | LOW | NONE
    notes: str = ""


class PriceShockOutput(BaseModel):
    entry_points: list[PriceShockEntry] = Field(default_factory=list)
    primary_entry: str = ""
    price_pipeline_summary: str = ""


# ---------------------------------------------------------------------------
# Phase 2: Pass-Through + Baseline
# ---------------------------------------------------------------------------

class PassThroughEstimate(BaseModel):
    category: str = ""          # "food_away", "groceries", "retail", "gas", etc.
    pass_through_rate: str = ""  # e.g., "60-100%"
    market_structure: str = ""
    demand_elasticity: str = ""
    evidence: str = ""
    time_horizon: str = ""


class CategoryBaseline(BaseModel):
    category: str = ""
    current_cpi_value: str = ""
    cpi_series_id: str = ""
    recent_trend: str = ""
    budget_share_low_income: str = ""
    budget_share_middle_income: str = ""
    budget_share_high_income: str = ""


class PassThroughBaselineOutput(BaseModel):
    pass_through_estimates: list[PassThroughEstimate] = Field(default_factory=list)
    category_baselines: list[CategoryBaseline] = Field(default_factory=list)
    ppi_data: list[str] = Field(default_factory=list)
    income_baselines: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 3: Geographic + Behavioral
# ---------------------------------------------------------------------------

class RegionalPriceImpact(BaseModel):
    region: str = ""
    rpp_adjustment: str = ""    # e.g., "RPP 115 → 15% above national"
    competitive_intensity: str = ""
    adjusted_price_changes: dict[str, str] = Field(default_factory=dict)  # category → adjusted $/month
    substitution_notes: str = ""


class GeoBehavioralOutput(BaseModel):
    regional_impacts: list[RegionalPriceImpact] = Field(default_factory=list)
    substitution_patterns: list[str] = Field(default_factory=list)
    quality_adjustment_risks: list[str] = Field(default_factory=list)
    computation_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 4: Net Purchasing Power
# ---------------------------------------------------------------------------

class HouseholdProfile(BaseModel):
    name: str = ""              # e.g., "Directly affected worker ($15/hr)"
    income_level: str = ""
    household_type: str = ""    # "renter_with_children", "single_renter", "retiree", etc.
    income_change: str = ""     # from policy (wage gain, tax change, transfer)
    price_changes_by_category: dict[str, str] = Field(default_factory=dict)  # category → $/month
    total_monthly_cost_change: str = ""
    net_purchasing_power_change: str = ""
    net_annual_change: str = ""
    pct_of_income: str = ""
    verdict: str = ""           # "better_off" | "worse_off" | "neutral"


class TemporalPriceEffect(BaseModel):
    phase: str = ""             # "anticipation" | "initial_shock" | "adjustment" | "steady_state"
    duration: str = ""
    description: str = ""
    magnitude: str = ""


class PurchasingPowerOutput(BaseModel):
    household_profiles: list[HouseholdProfile] = Field(default_factory=list)
    temporal_effects: list[TemporalPriceEffect] = Field(default_factory=list)
    benefits_cliff_risk: str = ""
    second_round_effects: str = ""
    computation_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 5: Consumer Impact Scorecard + Report
# ---------------------------------------------------------------------------

class ConsumerScorecard(BaseModel):
    region: str = ""
    income_tier: str = ""
    household_type: str = ""
    monthly_income_pretax: str = ""
    monthly_income_posttax: str = ""
    # Income side
    direct_income_change: str = ""
    tax_transfer_change: str = ""
    total_income_change: str = ""
    # Price side (per category)
    groceries_change: str = ""
    restaurants_change: str = ""
    transportation_change: str = ""
    utilities_change: str = ""
    healthcare_change: str = ""
    childcare_change: str = ""
    retail_goods_change: str = ""
    housing_change: str = ""    # from Housing Agent
    other_services_change: str = ""
    total_cost_change: str = ""
    # Net
    net_monthly_change: str = ""
    net_annual_change: str = ""
    pct_of_income: str = ""
    verdict: str = ""           # "Better off" | "Worse off" | "Roughly neutral"
    confidence: str = ""
    primary_driver: str = ""
    timeline: str = ""


class ConsumerImpactScorecard(BaseModel):
    scorecards: list[ConsumerScorecard] = Field(default_factory=list)
    methodology_notes: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class CausalClaimSimple(BaseModel):
    claim: str = ""
    cause: str = ""
    effect: str = ""
    mechanism: str = ""
    confidence: str = "THEORETICAL"
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    sensitivity: str | None = None


class ConsumerReport(BaseModel):
    sector: str = "consumer"
    direct_effects: list[CausalClaimSimple] = Field(default_factory=list)
    second_order_effects: list[CausalClaimSimple] = Field(default_factory=list)
    feedback_loops: list[CausalClaimSimple] = Field(default_factory=list)
    cross_sector_dependencies: list[str] = Field(default_factory=list)
    dissent: str | None = None

    # Consumer-specific phase outputs
    price_shock_analysis: PriceShockOutput | None = None
    pass_through_baseline: PassThroughBaselineOutput | None = None
    geo_behavioral: GeoBehavioralOutput | None = None
    purchasing_power: PurchasingPowerOutput | None = None
    consumer_impact_scorecard: ConsumerImpactScorecard | None = None


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------

class ConsumerState(TypedDict, total=False):
    analyst_briefing: AnalystBriefing
    policy_query: str
    current_phase: int
    phase_1_output: PriceShockOutput | None
    phase_2_output: PassThroughBaselineOutput | None
    phase_3_output: GeoBehavioralOutput | None
    phase_4_output: PurchasingPowerOutput | None
    phase_5_output: ConsumerReport | None
    # LLM-generated summaries
    phase_2_summary: str | None
    phase_3_summary: str | None
    phase_4_summary: str | None
    tool_call_log: list[ToolCallRecord]

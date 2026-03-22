from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stage 0: Classifier Output (powered by Google ADK)
# ---------------------------------------------------------------------------

class PolicyTaskType(str, Enum):
    MINIMUM_WAGE       = "minimum_wage"
    TRADE_TARIFF       = "trade_tariff"
    IMMIGRATION        = "immigration"
    TAX_POLICY         = "tax_policy"
    HOUSING_REGULATION = "housing_regulation"
    HEALTHCARE         = "healthcare"
    EDUCATION          = "education"
    ENVIRONMENTAL      = "environmental"
    OTHER              = "other"


class ClassifierOutput(BaseModel):
    task_type:     PolicyTaskType       = Field(description="Detected policy category")
    policy_params: dict[str, str]       = Field(default_factory=dict, description="Key policy parameters extracted from the query (action, value, scope, timeline, …)")
    confidence:    str                  = Field(description="Classification confidence: high | medium | low")
    cleaned_query: str                  = Field(description="Normalised, unambiguous version of the user's input")
    reasoning:     str                  = Field(default="", description="One-sentence explanation of the classification")


# ---------------------------------------------------------------------------
# Confidence levels (shared across all phases)
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, Enum):
    EMPIRICAL = "EMPIRICAL"
    THEORETICAL = "THEORETICAL"
    SPECULATIVE = "SPECULATIVE"


# ---------------------------------------------------------------------------
# Phase 1: Policy Specification
# ---------------------------------------------------------------------------

class PolicySpec(BaseModel):
    action: str = Field(description="What the policy does, e.g. 'Raise the federal minimum wage'")
    value: str = Field(description="Specific value/magnitude, e.g. '$15 per hour'")
    scope: str = Field(description="Geographic/jurisdictional scope, e.g. 'Federal, all covered employers'")
    timeline: str = Field(description="Implementation timeline/phase-in schedule")
    exemptions: list[str] = Field(default_factory=list, description="Known exemptions or carve-outs")
    enforcement_mechanism: str = Field(default="", description="How the policy is enforced")
    current_baseline: str = Field(description="Current state of the policy variable")
    ambiguities: list[str] = Field(default_factory=list, description="Unresolved specification questions")
    working_assumptions: list[str] = Field(default_factory=list, description="Assumptions made to resolve ambiguities")
    political_context: str = Field(default="", description="Current legislative status and political context")


# ---------------------------------------------------------------------------
# Phase 2: Baseline & Counterfactual
# ---------------------------------------------------------------------------

class BaselineMetric(BaseModel):
    metric_name: str
    series_id: str = ""
    source: str = ""
    latest_value: str = ""
    latest_date: str = ""
    trend_description: str = ""
    relevance: str = ""


class PolicyBite(BaseModel):
    segment: str
    current_level: str = ""
    proposed_level: str = ""
    bite_magnitude: str = ""
    data_source: str = ""


class BaselineOutput(BaseModel):
    key_metrics: list[BaselineMetric] = Field(default_factory=list)
    existing_trends: list[str] = Field(default_factory=list)
    scheduled_changes: list[str] = Field(default_factory=list)
    policy_bite: list[PolicyBite] = Field(default_factory=list)
    counterfactual_summary: str = ""


# ---------------------------------------------------------------------------
# Phase 3: Transmission Channel Mapping
# ---------------------------------------------------------------------------

class TransmissionChannel(BaseModel):
    name: str
    mechanism: str
    who_affected: list[str] = Field(default_factory=list)
    direction: str = ""
    magnitude_estimate: str = ""
    confidence: str = "THEORETICAL"
    empirically_studied: bool = False
    notes: str = ""


class TransmissionMapOutput(BaseModel):
    channels: list[TransmissionChannel] = Field(default_factory=list)
    primary_channels: list[str] = Field(default_factory=list)
    cross_sector_interactions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 4: Evidence Gathering
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    channel_name: str
    source_type: str = ""
    title: str = ""
    authors: str | None = ""
    year: int | None = None
    key_finding: str = ""
    effect_size: str = ""
    study_context: str = ""
    applicability: str = ""
    confidence: str = "THEORETICAL"
    url: str = ""


class EvidenceOutput(BaseModel):
    evidence_by_channel: dict[str, list[EvidenceItem]] = Field(default_factory=dict)
    literature_consensus: list[str] = Field(default_factory=list)
    literature_disputes: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    search_queries_used: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 5: Analyst Briefing (Final Output)
# ---------------------------------------------------------------------------

class SectorExposure(BaseModel):
    sector: str
    exposure_level: str = ""
    primary_channels: list[str] = Field(default_factory=list)
    notes: str = ""


class AnalystBriefing(BaseModel):
    # Executive Summary
    executive_summary: str = ""
    key_findings: list[str] = Field(default_factory=list)
    critical_uncertainties: list[str] = Field(default_factory=list)

    # From prior phases
    policy_spec: PolicySpec | None = None
    baseline: BaselineOutput | None = None
    transmission_channels: list[TransmissionChannel] = Field(default_factory=list)

    # Distributional Analysis
    distributional_by_income: list[str] = Field(default_factory=list)
    distributional_by_geography: list[str] = Field(default_factory=list)
    distributional_by_industry: list[str] = Field(default_factory=list)
    distributional_by_firm_size: list[str] = Field(default_factory=list)
    distributional_by_demographic: list[str] = Field(default_factory=list)

    # Fiscal Impact
    revenue_effects: str = ""
    transfer_program_effects: str = ""
    government_cost_effects: str = ""

    # Sector Exposure Matrix
    sector_exposure: list[SectorExposure] = Field(default_factory=list)

    # Evidence Base
    evidence: EvidenceOutput | None = None

    # Uncertainties & Sensitivity
    key_assumptions: list[str] = Field(default_factory=list)
    sensitivity_factors: list[str] = Field(default_factory=list)
    scenarios: dict[str, str] = Field(default_factory=dict)

    # Analogous Cases
    analogous_cases: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool Call Audit Record
# ---------------------------------------------------------------------------

class ToolCallRecord(BaseModel):
    phase: int
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    result_summary: str = ""
    timestamp: str = ""

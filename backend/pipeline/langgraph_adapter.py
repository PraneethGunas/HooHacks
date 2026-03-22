"""
Adapter layer: Rudra's LangGraph sector agents → pipeline SectorReport.

Housing and Consumer agents produce HousingReport / ConsumerReport with
CausalClaimSimple (string confidence). This module converts them into the
pipeline's SectorReport with CausalClaim (enum confidence) so synthesis
and the frontend work unchanged.

Also bridges the pipeline's briefing dict → AnalystBriefing Pydantic model
that the LangGraph agents expect as input.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.agents.schemas import (
    AnalystBriefing,
    BaselineMetric,
    BaselineOutput,
    EvidenceOutput,
    PolicySpec,
    SectorExposure,
    ToolCallRecord as AgentToolCallRecord,
    TransmissionChannel,
)
from backend.agents.housing.schemas import HousingReport
from backend.agents.consumer.schemas import ConsumerReport
from backend.models.pipeline import (
    CausalClaim,
    ConfidenceLevel,
    SectorReport,
    ToolCallRecord,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Confidence conversion: string → enum
# ---------------------------------------------------------------------------

def _to_confidence(raw: str) -> ConfidenceLevel:
    """Convert a string confidence (from CausalClaimSimple) to our enum."""
    if not isinstance(raw, str):
        return ConfidenceLevel.THEORETICAL
    v = raw.lower().strip()
    if v in ("empirical", "high", "strong", "data-backed", "data_backed"):
        return ConfidenceLevel.EMPIRICAL
    if v in ("theoretical", "medium", "moderate", "model-based"):
        return ConfidenceLevel.THEORETICAL
    if v in ("speculative", "low", "weak", "uncertain"):
        return ConfidenceLevel.SPECULATIVE
    return ConfidenceLevel.THEORETICAL


# ---------------------------------------------------------------------------
# CausalClaimSimple → CausalClaim
# ---------------------------------------------------------------------------

def _convert_claim(simple: Any) -> CausalClaim:
    """Convert a CausalClaimSimple (or dict) into a pipeline CausalClaim."""
    if hasattr(simple, "model_dump"):
        d = simple.model_dump()
    elif isinstance(simple, dict):
        d = simple
    else:
        return CausalClaim(
            claim=str(simple), cause="", effect="",
            mechanism="unspecified", confidence=ConfidenceLevel.SPECULATIVE,
        )
    return CausalClaim(
        claim=d.get("claim", ""),
        cause=d.get("cause", ""),
        effect=d.get("effect", ""),
        mechanism=d.get("mechanism", "unspecified"),
        confidence=_to_confidence(d.get("confidence", "theoretical")),
        evidence=d.get("evidence", []),
        assumptions=d.get("assumptions", []),
        sensitivity=d.get("sensitivity"),
    )


# ---------------------------------------------------------------------------
# ToolCallRecord conversion (agents schema → pipeline schema)
# ---------------------------------------------------------------------------

def _convert_tool_records(records: list[AgentToolCallRecord]) -> list[ToolCallRecord]:
    """Convert Rudra's ToolCallRecord (phase-aware) to the pipeline ToolCallRecord."""
    return [
        ToolCallRecord(
            tool=r.tool_name,
            query=r.arguments if isinstance(r.arguments, str) else json.dumps(r.arguments),
            success=True,
            summary=r.result_summary,
        )
        for r in records
    ]


# ---------------------------------------------------------------------------
# HousingReport / ConsumerReport → SectorReport
# ---------------------------------------------------------------------------

def housing_report_to_sector_report(
    report: HousingReport,
    tool_records: list[AgentToolCallRecord] | None = None,
) -> SectorReport:
    """Convert a HousingReport to the pipeline SectorReport format."""
    return SectorReport(
        sector="housing",
        direct_effects=[_convert_claim(c) for c in report.direct_effects],
        second_order_effects=[_convert_claim(c) for c in report.second_order_effects],
        feedback_loops=[_convert_claim(c) for c in report.feedback_loops],
        cross_sector_dependencies=report.cross_sector_dependencies,
        dissent=report.dissent,
        tool_calls_made=_convert_tool_records(tool_records or []),
        agent_mode="agentic",
    )


def consumer_report_to_sector_report(
    report: ConsumerReport,
    tool_records: list[AgentToolCallRecord] | None = None,
) -> SectorReport:
    """Convert a ConsumerReport to the pipeline SectorReport format."""
    return SectorReport(
        sector="consumer",
        direct_effects=[_convert_claim(c) for c in report.direct_effects],
        second_order_effects=[_convert_claim(c) for c in report.second_order_effects],
        feedback_loops=[_convert_claim(c) for c in report.feedback_loops],
        cross_sector_dependencies=report.cross_sector_dependencies,
        dissent=report.dissent,
        tool_calls_made=_convert_tool_records(tool_records or []),
        agent_mode="agentic",
    )


# ---------------------------------------------------------------------------
# Pipeline briefing dict → AnalystBriefing
# ---------------------------------------------------------------------------

def briefing_dict_to_analyst_briefing(briefing: dict[str, Any]) -> AnalystBriefing:
    """
    Convert the pipeline's briefing dict (from Stage 1) into the AnalystBriefing
    Pydantic model that Rudra's LangGraph agents expect.

    The pipeline analyst stores a flat dict; the agents expect structured fields.
    We do best-effort mapping — missing fields get sensible defaults.
    """
    # If briefing is already an AnalystBriefing, return it
    if isinstance(briefing, AnalystBriefing):
        return briefing

    # Build PolicySpec if available
    policy_spec = None
    ps = briefing.get("policy_spec") or briefing.get("policy_specification")
    if isinstance(ps, dict):
        policy_spec = PolicySpec(
            action=ps.get("action", ""),
            value=ps.get("value", ""),
            scope=ps.get("scope", ""),
            timeline=ps.get("timeline", ""),
            exemptions=ps.get("exemptions", []),
            enforcement_mechanism=ps.get("enforcement_mechanism", ""),
            current_baseline=ps.get("current_baseline", ""),
            ambiguities=ps.get("ambiguities", []),
            working_assumptions=ps.get("working_assumptions", []),
            political_context=ps.get("political_context", ""),
        )

    # Build BaselineOutput if available
    baseline = None
    bl = briefing.get("baseline") or briefing.get("baseline_data")
    if isinstance(bl, dict):
        metrics = []
        for m in bl.get("key_metrics", []):
            if isinstance(m, dict):
                metrics.append(BaselineMetric(**{k: m.get(k, "") for k in BaselineMetric.model_fields}))
        baseline = BaselineOutput(
            key_metrics=metrics,
            existing_trends=bl.get("existing_trends", []),
            scheduled_changes=bl.get("scheduled_changes", []),
            counterfactual_summary=bl.get("counterfactual_summary", ""),
        )

    # Build TransmissionChannels if available
    channels = []
    for ch in briefing.get("transmission_channels", []):
        if isinstance(ch, dict):
            channels.append(TransmissionChannel(
                name=ch.get("name", ""),
                mechanism=ch.get("mechanism", ""),
                who_affected=ch.get("who_affected", []),
                direction=ch.get("direction", ""),
                magnitude_estimate=ch.get("magnitude_estimate", ""),
                confidence=ch.get("confidence", "theoretical"),
                notes=ch.get("notes", ""),
            ))

    # Build SectorExposure if available
    sector_exposure = []
    for se in briefing.get("sector_exposure", []):
        if isinstance(se, dict):
            sector_exposure.append(SectorExposure(
                sector=se.get("sector", ""),
                exposure_level=se.get("exposure_level", ""),
                primary_channels=se.get("primary_channels", []),
                notes=se.get("notes", ""),
            ))

    # Build EvidenceOutput if available
    evidence = None
    ev = briefing.get("evidence")
    if isinstance(ev, dict):
        evidence = EvidenceOutput(
            evidence_by_channel=ev.get("evidence_by_channel", {}),
            literature_consensus=ev.get("literature_consensus", []),
            literature_disputes=ev.get("literature_disputes", []),
            evidence_gaps=ev.get("evidence_gaps", []),
        )

    return AnalystBriefing(
        executive_summary=briefing.get("executive_summary", briefing.get("summary", "")),
        key_findings=briefing.get("key_findings", []),
        critical_uncertainties=briefing.get("critical_uncertainties", []),
        policy_spec=policy_spec,
        baseline=baseline,
        transmission_channels=channels,
        distributional_by_income=briefing.get("distributional_by_income", []),
        distributional_by_geography=briefing.get("distributional_by_geography", []),
        distributional_by_industry=briefing.get("distributional_by_industry", []),
        distributional_by_firm_size=briefing.get("distributional_by_firm_size", []),
        distributional_by_demographic=briefing.get("distributional_by_demographic", []),
        revenue_effects=briefing.get("revenue_effects", ""),
        transfer_program_effects=briefing.get("transfer_program_effects", ""),
        government_cost_effects=briefing.get("government_cost_effects", ""),
        sector_exposure=sector_exposure,
        evidence=evidence,
        key_assumptions=briefing.get("key_assumptions", []),
        sensitivity_factors=briefing.get("sensitivity_factors", []),
        scenarios=briefing.get("scenarios", {}),
        analogous_cases=briefing.get("analogous_cases", []),
    )

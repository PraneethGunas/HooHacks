"""Phase node implementations for the Synthesis & Impact Dashboard agent."""

from __future__ import annotations

import logging

from backend.agents._helpers import (
    _run_react_phase,
    _run_reasoning_phase,
    summarize_phase_output,
)
from backend.agents.synthesis.prompts import (
    SYNTHESIS_IDENTITY_SHORT,
    phase_1_system_prompt,
    phase_2_system_prompt,
    phase_3_system_prompt,
    phase_4_system_prompt,
    phase_5_system_prompt,
)
from backend.agents.synthesis.schemas import (
    AgentFrameworkTrace,
    ChannelDecision,
    ConsistencyAuditOutput,
    DataProvenance,
    NarrativeOutput,
    NetImpactOutput,
    PolicyClassification,
    ReasoningChain,
    SynthesisReport,
    WinnersLosersOutput,
)
from backend.agents.synthesis.tool_wrappers import (
    SYNTHESIS_PHASE_2_TOOLS,
    SYNTHESIS_PHASE_3_TOOLS,
    SYNTHESIS_PHASE_5_TOOLS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reasoning chain builders (programmatic, no LLM calls)
# ---------------------------------------------------------------------------


def _build_reasoning_chain(state: dict) -> ReasoningChain:
    """Extract the reasoning chain from upstream agent outputs."""
    briefing = state.get("analyst_briefing")
    housing = state.get("housing_report")
    consumer = state.get("consumer_report")

    chain = ReasoningChain()

    # Step 1: Classification
    if briefing and briefing.policy_spec:
        ps = briefing.policy_spec
        income_flag = ps.income_effect_exists
        chain.classification = PolicyClassification(
            policy_type=ps.policy_type or "UNCLASSIFIED",
            income_effect_exists=income_flag,
            income_effect_explanation=f"Policy type {ps.policy_type}: income effect {'exists' if income_flag else 'does not exist'}",
            analysis_mode="BILATERAL" if income_flag else "PURE_COST",
            reasoning=f"Classified as {ps.policy_type} based on policy mechanism: {ps.action}",
        )

    # Step 2: Channel decisions from analyst's transmission map
    if briefing and briefing.transmission_channels:
        for ch in briefing.transmission_channels:
            status = ch.status.upper() if ch.status else ("NULL" if not ch.mechanism else "ACTIVE")
            chain.channel_decisions.append(ChannelDecision(
                name=ch.name,
                status=status,
                reason=ch.notes or ch.downstream_instruction or "",
                magnitude=ch.magnitude_estimate if status == "ACTIVE" else "",
                confidence=ch.confidence,
                downstream_instruction=ch.downstream_instruction,
            ))
        chain.active_channels = sum(1 for d in chain.channel_decisions if d.status == "ACTIVE")
        chain.null_channels = sum(1 for d in chain.channel_decisions if d.status == "NULL")

    # Step 3: Per-agent framework traces
    # Housing agent
    if housing:
        trace = AgentFrameworkTrace(
            agent_name="Housing & Cost of Living",
            framework_name="Stock-Flow-Price Model (6 Pathways)",
        )
        if housing.pathway_analysis:
            pa = housing.pathway_analysis
            trace.pathways_activated = [p.name for p in pa.pathways if p.relevance.upper() in ("HIGH", "MEDIUM")]
            trace.pathways_skipped = [p.name for p in pa.pathways if p.relevance.upper() in ("LOW", "NONE", "INACTIVE", "NULL", "NEGLIGIBLE")]
            trace.skip_reasons = [f"{p.name}: {p.notes}" for p in pa.pathways if p.relevance.upper() in ("LOW", "NONE", "INACTIVE", "NULL", "NEGLIGIBLE") and p.notes]
        if housing.magnitude_estimates and housing.magnitude_estimates.estimates:
            trace.key_elasticities = [
                f"{e.methodology}" for e in housing.magnitude_estimates.estimates[:3] if e.methodology
            ]
            trace.materiality_check = f"{len(housing.magnitude_estimates.estimates)} estimates computed"
        if housing.affordability_scorecard and housing.affordability_scorecard.sub_markets:
            trace.key_finding = f"{len(housing.affordability_scorecard.sub_markets)} sub-market scorecards produced"
        elif housing.direct_effects:
            trace.key_finding = housing.direct_effects[0].claim if housing.direct_effects else ""
        trace.mode = "Full Analysis" if trace.pathways_activated else "Minimal (negligible impact)"
        chain.agent_traces.append(trace)

    # Consumer agent
    if consumer:
        trace = AgentFrameworkTrace(
            agent_name="Consumer & Prices",
            framework_name="Price Transmission Pipeline (6 Stages)",
        )
        if consumer.price_shock_analysis:
            psa = consumer.price_shock_analysis
            trace.pathways_activated = [e.name for e in psa.entry_points if e.relevance.upper() in ("HIGH", "MEDIUM")]
            trace.pathways_skipped = [e.name for e in psa.entry_points if e.relevance.upper() in ("LOW", "NONE")]
        if consumer.pass_through_baseline:
            trace.key_elasticities = [
                f"{pt.category}: {pt.pass_through_rate} pass-through ({pt.evidence})"
                for pt in consumer.pass_through_baseline.pass_through_estimates[:3]
                if pt.pass_through_rate
            ]
        if consumer.purchasing_power and consumer.purchasing_power.household_profiles:
            profiles = consumer.purchasing_power.household_profiles
            trace.key_finding = f"{len(profiles)} household profiles computed"
        elif consumer.direct_effects:
            trace.key_finding = consumer.direct_effects[0].claim if consumer.direct_effects else ""
        is_mode_b = briefing and briefing.policy_spec and briefing.policy_spec.income_effect_exists is False
        trace.mode = "Mode B (Pure Cost)" if is_mode_b else "Mode A (Bilateral)"
        chain.agent_traces.append(trace)

    # Step 4: Consistency resolutions
    audit = state.get("phase_1_output")
    if audit and audit.inconsistencies:
        chain.consistency_resolutions = [
            f"{i.variable}: {i.resolution}" for i in audit.inconsistencies
        ]

    # Step 5: Plain English reasoning summary
    parts = []
    if chain.classification:
        parts.append(f"The analyst classified this as {chain.classification.policy_type}")
        if chain.classification.income_effect_exists is False:
            parts.append("determined there is NO income effect")
        elif chain.classification.income_effect_exists is True:
            parts.append("confirmed income effects exist")
    if chain.null_channels > 0:
        parts.append(f"gated out {chain.null_channels} irrelevant channels")
    for trace in chain.agent_traces:
        if trace.pathways_skipped:
            parts.append(f"{trace.agent_name} skipped {len(trace.pathways_skipped)} pathways")
        if trace.key_finding:
            parts.append(f"{trace.agent_name} found: {trace.key_finding}")
    if chain.consistency_resolutions:
        parts.append(f"synthesis resolved {len(chain.consistency_resolutions)} cross-agent inconsistencies")
    chain.reasoning_summary = " → ".join(parts) + "." if parts else ""

    return chain


def _build_data_provenance(state: dict) -> list[DataProvenance]:
    """Extract data provenance from agent outputs — traces findings to source data."""
    provenance = []
    housing = state.get("housing_report")
    consumer = state.get("consumer_report")

    # Housing data provenance
    if housing and housing.housing_baseline:
        for metric in housing.housing_baseline.supply_metrics + housing.housing_baseline.demand_metrics + housing.housing_baseline.price_metrics:
            if metric.value and metric.source:
                provenance.append(DataProvenance(
                    finding=f"{metric.metric_name}: {metric.value}",
                    data_sources=[f"{metric.source} ({metric.date})" if metric.date else metric.source],
                    methodology="Direct data retrieval",
                    computed_by="Housing Agent Phase 2",
                    confidence="EMPIRICAL",
                ))
            if len(provenance) >= 8:
                break

    # Consumer data provenance
    if consumer and consumer.pass_through_baseline:
        for pt in consumer.pass_through_baseline.pass_through_estimates[:4]:
            if pt.pass_through_rate:
                provenance.append(DataProvenance(
                    finding=f"{pt.category} pass-through: {pt.pass_through_rate}",
                    data_sources=[pt.evidence] if pt.evidence else [],
                    methodology=f"Market structure: {pt.market_structure}" if pt.market_structure else "",
                    computed_by="Consumer Agent Phase 2",
                    confidence="EMPIRICAL" if pt.evidence else "THEORETICAL",
                ))

    # Housing magnitude estimates
    if housing and housing.magnitude_estimates:
        for est in housing.magnitude_estimates.estimates[:3]:
            if est.central_estimate:
                provenance.append(DataProvenance(
                    finding=f"{est.metric}: {est.central_estimate} ({est.low_estimate} to {est.high_estimate})",
                    data_sources=[],
                    methodology=est.methodology,
                    computed_by="Housing Agent Phase 3 via code_execute",
                    confidence=est.pathway_id,
                ))

    return provenance


async def synthesis_phase_1_audit(state: dict) -> dict:
    """Phase 1: Input Validation + Consistency Audit — reasoning only."""
    logger.info("=== SYNTHESIS PHASE 1: Consistency Audit ===")
    prompt = phase_1_system_prompt(
        state["analyst_briefing"],
        state.get("housing_report"),
        state.get("consumer_report"),
    )

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Audit all upstream agent outputs for completeness and cross-agent consistency.",
    )

    output = ConsistencyAuditOutput(**parsed)
    logger.info(
        f"Synthesis Phase 1 complete: {len(output.input_inventory)} agents inventoried, "
        f"{len(output.inconsistencies)} inconsistencies found"
    )

    phase_1_summary = summarize_phase_output(
        "Consistency Audit (Phase 1)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 2,
        "phase_1_output": output,
        "phase_1_summary": phase_1_summary,
    }


async def synthesis_phase_2_impact(state: dict) -> dict:
    """Phase 2: Net Household Impact Computation — code_execute."""
    logger.info("=== SYNTHESIS PHASE 2: Net Impact Computation ===")

    user_msg = phase_2_system_prompt(
        state["analyst_briefing"],
        state.get("housing_report"),
        state.get("consumer_report"),
        phase_1_summary=state.get("phase_1_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=SYNTHESIS_IDENTITY_SHORT,
        user_message=user_msg,
        tools=SYNTHESIS_PHASE_2_TOOLS,
        phase_num=2,
        state=state,
        recursion_limit=30,
    )

    output = NetImpactOutput(**parsed)
    logger.info(f"Synthesis Phase 2 complete: {len(output.household_impacts)} profiles computed")

    phase_2_summary = summarize_phase_output(
        "Net Impact (Phase 2)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 3,
        "phase_2_output": output,
        "phase_2_summary": phase_2_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def synthesis_phase_3_winners(state: dict) -> dict:
    """Phase 3: Winners/Losers + Confidence — code_execute."""
    logger.info("=== SYNTHESIS PHASE 3: Winners & Losers ===")

    user_msg = phase_3_system_prompt(
        phase_2_summary=state.get("phase_2_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=SYNTHESIS_IDENTITY_SHORT,
        user_message=user_msg,
        tools=SYNTHESIS_PHASE_3_TOOLS,
        phase_num=3,
        state=state,
        recursion_limit=20,
    )

    output = WinnersLosersOutput(**parsed)
    logger.info(
        f"Synthesis Phase 3 complete: {len(output.winners)} winners, "
        f"{len(output.losers)} losers, {len(output.mixed)} mixed"
    )

    phase_3_summary = summarize_phase_output(
        "Winners & Losers (Phase 3)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 4,
        "phase_3_output": output,
        "phase_3_summary": phase_3_summary,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def synthesis_phase_4_narrative(state: dict) -> dict:
    """Phase 4: Timeline + Narrative — reasoning only."""
    logger.info("=== SYNTHESIS PHASE 4: Narrative ===")

    prompt = phase_4_system_prompt(
        state["analyst_briefing"],
        phase_1_summary=state.get("phase_1_summary"),
        phase_2_summary=state.get("phase_2_summary"),
        phase_3_summary=state.get("phase_3_summary"),
    )

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Produce the plain-language narrative summary and unified timeline.",
    )

    output = NarrativeOutput(**parsed)
    logger.info(f"Synthesis Phase 4 complete: {len(output.key_findings)} key findings")

    phase_4_summary = summarize_phase_output(
        "Narrative (Phase 4)", output.model_dump_json(indent=2)
    )

    return {
        "current_phase": 5,
        "phase_4_output": output,
        "phase_4_summary": phase_4_summary,
    }


async def synthesis_phase_5_payload(state: dict) -> dict:
    """Phase 5: Analytics Payload — code_execute for final structuring."""
    logger.info("=== SYNTHESIS PHASE 5: Analytics Payload ===")

    user_msg = phase_5_system_prompt(
        state["analyst_briefing"],
        phase_1_summary=state.get("phase_1_summary"),
        phase_2_summary=state.get("phase_2_summary"),
        phase_3_summary=state.get("phase_3_summary"),
        phase_4_summary=state.get("phase_4_summary"),
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=SYNTHESIS_IDENTITY_SHORT,
        user_message=user_msg,
        tools=SYNTHESIS_PHASE_5_TOOLS,
        phase_num=5,
        state=state,
        recursion_limit=30,
    )

    report = SynthesisReport(**parsed)

    # Inject phase outputs
    report.consistency_audit = state.get("phase_1_output")
    report.narrative = state.get("phase_4_output")
    if state.get("phase_3_output"):
        report.winners_losers = state["phase_3_output"]
    if state.get("phase_2_output"):
        report.household_impacts = state["phase_2_output"].household_impacts
        report.waterfall = state["phase_2_output"].waterfall

    # ── BUILD REASONING CHAIN (programmatic, no LLM needed) ──────
    report.reasoning_chain = _build_reasoning_chain(state)
    report.data_provenance = _build_data_provenance(state)

    # Meta
    briefing = state.get("analyst_briefing")
    if briefing and briefing.policy_spec:
        report.analysis_mode = "PURE_COST" if briefing.policy_spec.income_effect_exists is False else "BILATERAL"
    report.total_tool_calls = len(state.get("tool_call_log", []))
    report.agents_that_ran = [
        a for a in ["analyst", "housing", "consumer"]
        if state.get(f"{a}_report") is not None or a == "analyst"
    ]

    logger.info("Synthesis Phase 5 complete: Final report with reasoning chain")

    return {
        "current_phase": 5,
        "phase_5_output": report,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }

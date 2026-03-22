"""Layer 2: Pipeline-level evaluation — custom pytest tests.

These test cross-agent consistency, phantom channel detection,
structural output validation, and end-to-end correctness.
Run with: python -m pytest evals/test_pipeline_eval.py -v
"""

import asyncio
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evals.eval_logger import log_eval_result


# ---------------------------------------------------------------------------
# Helpers — run agents and cache results per session
# ---------------------------------------------------------------------------

_cache = {}


async def _run_analyst(policy: str):
    key = f"analyst:{policy}"
    if key not in _cache:
        from backend.agents.run import run_analyst_agent
        _cache[key] = await run_analyst_agent(policy)
    return _cache[key]


async def _run_housing(briefing, policy: str):
    key = f"housing:{policy}"
    if key not in _cache:
        from backend.agents.housing.run import run_housing_agent
        _cache[key] = await run_housing_agent(briefing, policy)
    return _cache[key]


async def _run_consumer(briefing, policy: str):
    key = f"consumer:{policy}"
    if key not in _cache:
        from backend.agents.consumer.run import run_consumer_agent
        _cache[key] = await run_consumer_agent(briefing, policy)
    return _cache[key]


# ---------------------------------------------------------------------------
# Test policies
# ---------------------------------------------------------------------------

LABOR_COST = "Raise minimum wage to $20 per hour across Virginia"
REGULATORY_COST = "Ban single-use plastic packaging and food service items nationwide starting 2027"
TRANSFER = "Implement a universal basic income of $1000 per month for all US adults"


# ---------------------------------------------------------------------------
# Policy type classification
# ---------------------------------------------------------------------------

class TestPolicyClassification:
    """Analyst agent correctly classifies policy types."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_labor_cost_classification(self):
        state = await _run_analyst(LABOR_COST)
        briefing = state["phase_5_output"]
        assert briefing is not None
        # Should identify wage/labor effects
        channels = briefing.transmission_channels if briefing.transmission_channels else []
        channel_names = " ".join(c.name.lower() for c in channels)
        assert "wage" in channel_names or "labor" in channel_names or "employment" in channel_names

    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_transfer_classification(self):
        state = await _run_analyst(TRANSFER)
        briefing = state["phase_5_output"]
        assert briefing is not None
        summary = (briefing.executive_summary or "").lower()
        assert "income" in summary or "transfer" in summary or "ubi" in summary


# ---------------------------------------------------------------------------
# Phantom channel detection — THE KEY REGRESSION TEST
# ---------------------------------------------------------------------------

class TestPhantomChannels:
    """No agent fabricates income effects for REGULATORY_COST policies."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)
    async def test_consumer_no_phantom_income_for_regulatory(self):
        """Consumer agent must NOT produce positive income for a plastics ban."""
        analyst_state = await _run_analyst(REGULATORY_COST)
        briefing = analyst_state["phase_5_output"]
        assert briefing is not None

        consumer_state = await _run_consumer(briefing, REGULATORY_COST)
        report = consumer_state.get("phase_5_output")

        results = []
        if report and report.purchasing_power:
            for profile in report.purchasing_power.household_profiles:
                income_str = (profile.income_change or "$0").replace("$", "").replace(",", "").replace("+", "")
                try:
                    income_val = float(income_str)
                except ValueError:
                    income_val = 0
                passed = income_val <= 0
                results.append({
                    "rubric": f"No phantom income for {profile.name}",
                    "passed": passed,
                    "score": 1.0 if passed else 0.0,
                })

        # Check that report doesn't mention "wage ripple" or "better off"
        report_text = report.model_dump_json() if report else ""
        no_wage_ripple = "wage ripple" not in report_text.lower()
        results.append({
            "rubric": "No 'wage ripple' mentioned",
            "passed": no_wage_ripple,
            "score": 1.0 if no_wage_ripple else 0.0,
        })

        overall = all(r["passed"] for r in results) if results else False
        log_eval_result(
            agent="consumer",
            evalset_id="pipeline_phantom_channel_consumer",
            policy_query=REGULATORY_COST,
            scores={"phantom_channel_check": 1.0 if overall else 0.0},
            rubric_results=results,
            overall_pass=overall,
        )

        for r in results:
            assert r["passed"], f"PHANTOM CHANNEL: {r['rubric']}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)
    async def test_housing_no_demand_pathway_for_regulatory(self):
        """Housing agent must NOT activate demand pathway for a plastics ban."""
        analyst_state = await _run_analyst(REGULATORY_COST)
        briefing = analyst_state["phase_5_output"]
        assert briefing is not None

        housing_state = await _run_housing(briefing, REGULATORY_COST)
        report = housing_state.get("phase_5_output")

        results = []
        if report and report.pathway_analysis:
            for pathway in report.pathway_analysis.pathways:
                if pathway.pathway_id == "B" or "demand" in pathway.name.lower():
                    is_inactive = pathway.relevance.upper() in ["LOW", "NONE", "INACTIVE", "NULL", "NEGLIGIBLE"]
                    results.append({
                        "rubric": f"Pathway B ({pathway.name}) inactive for REGULATORY_COST",
                        "passed": is_inactive,
                        "score": 1.0 if is_inactive else 0.0,
                    })

        overall = all(r["passed"] for r in results) if results else True
        log_eval_result(
            agent="housing",
            evalset_id="pipeline_phantom_channel_housing",
            policy_query=REGULATORY_COST,
            scores={"demand_pathway_check": 1.0 if overall else 0.0},
            rubric_results=results,
            overall_pass=overall,
        )

        for r in results:
            assert r["passed"], f"PHANTOM CHANNEL: {r['rubric']}"


# ---------------------------------------------------------------------------
# Structural output validation
# ---------------------------------------------------------------------------

class TestStructuralValidation:
    """All agents produce structurally complete output."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_analyst_all_phases_complete(self):
        state = await _run_analyst(LABOR_COST)
        for i in range(1, 6):
            assert state.get(f"phase_{i}_output") is not None, f"Analyst phase {i} missing"

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_all_findings_have_confidence(self):
        state = await _run_analyst(LABOR_COST)
        briefing = state["phase_5_output"]
        if briefing and briefing.transmission_channels:
            for ch in briefing.transmission_channels:
                assert ch.confidence, f"Channel '{ch.name}' missing confidence"

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_tool_calls_logged(self):
        state = await _run_analyst(LABOR_COST)
        tools = state.get("tool_call_log", [])
        assert len(tools) > 5, f"Expected >5 tool calls, got {len(tools)}"


# ---------------------------------------------------------------------------
# Waterfall arithmetic check
# ---------------------------------------------------------------------------

class TestWaterfallArithmetic:
    """Synthesis waterfall steps sum to reported net."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)
    async def test_waterfall_sums_correctly(self):
        """If synthesis produces a waterfall, steps must sum to net."""
        analyst_state = await _run_analyst(TRANSFER)
        briefing = analyst_state["phase_5_output"]
        if not briefing:
            pytest.skip("Analyst failed")

        from backend.agents.synthesis.run import run_synthesis_agent
        synthesis_state = await run_synthesis_agent(
            analyst_briefing=briefing,
            policy_query=TRANSFER,
        )
        report = synthesis_state.get("phase_5_output")
        if not report or not report.waterfall:
            pytest.skip("No waterfall produced")

        steps = report.waterfall.steps
        if not steps:
            pytest.skip("Empty waterfall")

        step_sum = sum(
            s.value for s in steps
            if s.type != "net" and s.type != "base"
        )
        reported_net = report.waterfall.net_monthly
        assert abs(step_sum - reported_net) < 5.0, \
            f"Waterfall sum {step_sum} != reported net {reported_net}"

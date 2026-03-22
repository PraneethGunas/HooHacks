"""Full pipeline integration test: Analyst → [Housing ‖ Consumer] → Synthesis."""

import asyncio
import pytest
from backend.agents.run import run_analyst_agent
from backend.agents.housing.run import run_housing_agent
from backend.agents.consumer.run import run_consumer_agent
from backend.agents.synthesis.run import run_synthesis_agent
from backend.agents.synthesis.schemas import SynthesisReport


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_full_pipeline_minimum_wage():
    """End-to-end pipeline test with parallel sector agents."""
    query = "Raise the federal minimum wage to $15/hr"

    # Stage 1: Analyst
    analyst_state = await run_analyst_agent(query)
    briefing = analyst_state["phase_5_output"]
    assert briefing is not None
    analyst_tools = len(analyst_state.get("tool_call_log", []))

    # Stage 2: Housing + Consumer in PARALLEL
    housing_task = asyncio.create_task(run_housing_agent(briefing, query))
    consumer_task = asyncio.create_task(run_consumer_agent(briefing, query))
    housing_state, consumer_state = await asyncio.gather(housing_task, consumer_task)

    housing_report = housing_state.get("phase_5_output")
    consumer_report = consumer_state.get("phase_5_output")
    housing_tools = len(housing_state.get("tool_call_log", []))
    consumer_tools = len(consumer_state.get("tool_call_log", []))

    # Stage 3: Synthesis
    synthesis_state = await run_synthesis_agent(
        analyst_briefing=briefing,
        housing_report=housing_report,
        consumer_report=consumer_report,
        policy_query=query,
    )
    synthesis_tools = len(synthesis_state.get("tool_call_log", []))

    # Verify final report
    report = synthesis_state.get("phase_5_output")
    assert report is not None
    assert isinstance(report, SynthesisReport)

    # Summary
    total_tools = analyst_tools + housing_tools + consumer_tools + synthesis_tools
    print(f"\n{'='*60}")
    print(f"FULL PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"Analyst: {analyst_tools} tool calls")
    print(f"Housing: {housing_tools} tool calls")
    print(f"Consumer: {consumer_tools} tool calls")
    print(f"Synthesis: {synthesis_tools} tool calls")
    print(f"Total: {total_tools} tool calls")
    if report.narrative:
        print(f"\nBottom line: {report.narrative.bottom_line}")
    if report.winners_losers:
        print(f"Verdict: {report.winners_losers.distributional_verdict}")
    print(f"Confidence: {report.overall_confidence}")


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_full_pipeline_different_policy():
    """Verify pipeline works on a non-minimum-wage policy."""
    query = "Implement a universal basic income of $1000 per month for all US adults"

    analyst_state = await run_analyst_agent(query)
    briefing = analyst_state["phase_5_output"]
    assert briefing is not None

    # Run sector agents in parallel
    housing_task = asyncio.create_task(run_housing_agent(briefing, query))
    consumer_task = asyncio.create_task(run_consumer_agent(briefing, query))
    housing_state, consumer_state = await asyncio.gather(housing_task, consumer_task)

    synthesis_state = await run_synthesis_agent(
        analyst_briefing=briefing,
        housing_report=housing_state.get("phase_5_output"),
        consumer_report=consumer_state.get("phase_5_output"),
        policy_query=query,
    )

    report = synthesis_state.get("phase_5_output")
    assert report is not None
    print(f"\nUBI pipeline complete: {report.policy_title}")
    if report.narrative:
        print(f"Bottom line: {report.narrative.bottom_line}")

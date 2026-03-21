import pytest
from backend.agents.run import run_analyst_agent
from backend.agents.schemas import AnalystBriefing


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_analyst_agent_minimum_wage():
    """Full integration test: run analyst agent on minimum wage policy."""
    result = await run_analyst_agent("Raise the federal minimum wage to $15/hr")

    # Phase 1 completed
    assert result["phase_1_output"] is not None, "Phase 1 did not produce output"
    assert result["phase_1_output"].action, "Phase 1 action is empty"
    print(f"\nPhase 1: {result['phase_1_output'].action} — {result['phase_1_output'].value}")

    # Phase 2 completed
    assert result["phase_2_output"] is not None, "Phase 2 did not produce output"
    assert len(result["phase_2_output"].key_metrics) > 0, "Phase 2 has no metrics"
    print(f"Phase 2: {len(result['phase_2_output'].key_metrics)} baseline metrics")

    # Phase 3 completed
    assert result["phase_3_output"] is not None, "Phase 3 did not produce output"
    assert len(result["phase_3_output"].channels) >= 3, "Phase 3 has fewer than 3 channels"
    print(f"Phase 3: {len(result['phase_3_output'].channels)} transmission channels")

    # Phase 4 completed
    assert result["phase_4_output"] is not None, "Phase 4 did not produce output"
    print(f"Phase 4: evidence for {len(result['phase_4_output'].evidence_by_channel)} channels")

    # Phase 5 completed
    briefing = result["phase_5_output"]
    assert isinstance(briefing, AnalystBriefing), "Phase 5 did not produce AnalystBriefing"
    assert briefing.executive_summary, "Briefing has no executive summary"
    assert len(briefing.key_findings) >= 3, "Briefing has fewer than 3 key findings"
    print(f"Phase 5: Briefing with {len(briefing.key_findings)} findings, {len(briefing.sector_exposure)} sectors")

    # Audit trail
    tool_calls = result.get("tool_call_log", [])
    assert len(tool_calls) > 0, "No tool calls recorded"
    print(f"\nTotal tool calls: {len(tool_calls)}")

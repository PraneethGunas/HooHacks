"""
Stage 1: Analyst Agent — 5-phase LangGraph agentic pipeline.

Uses Rudra's LangGraph analyst agent (backend/agents/) which runs 5 phases:
  Phase 1: Policy Specification (ReAct — web search, doc fetch, FRED)
  Phase 2: Baseline & Counterfactual (ReAct — FRED, BLS)
  Phase 3: Transmission Channel Mapping (reasoning only)
  Phase 4: Evidence Gathering (ReAct — academic search, CBO, news)
  Phase 5: Synthesis & Briefing (reasoning only)

Each phase emits SSE events so the frontend shows live progress.

Falls back to simple hardcoded tool calls if LangGraph is unavailable.

===========================================================================
INTEGRATION GUIDE
===========================================================================
This stage now uses the FULL LangGraph agentic analyst from backend/agents/.
The agent makes 12-18 real tool calls across 3 ReAct phases, interleaved
with 2 pure-reasoning phases, producing a structured AnalystBriefing.

The briefing is converted to the pipeline's dict format and stored in
state.briefing for downstream sector agents.

OWNER: Rudra (agent quality) + Praneeth (pipeline integration + SSE)
===========================================================================
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Awaitable, Callable

from backend.pipeline.orchestrator import PipelineState
from backend.pipeline.llm import llm_chat, parse_json_response

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]

# Phase metadata for SSE events
ANALYST_PHASES = {
    1: {"name": "Policy Specification", "type": "react", "tools": ["web_search_news", "fetch_document_text", "fred_get_series"]},
    2: {"name": "Baseline & Counterfactual", "type": "react", "tools": ["fred_search", "fred_get_series", "bls_get_data"]},
    3: {"name": "Transmission Mapping", "type": "reasoning", "tools": []},
    4: {"name": "Evidence Gathering", "type": "react", "tools": ["search_academic_papers", "search_openalex", "search_cbo_reports", "fetch_document_text", "web_search_news"]},
    5: {"name": "Synthesis & Briefing", "type": "reasoning", "tools": []},
}


async def run_analyst(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 1: Run the full 5-phase LangGraph analyst agent."""
    await emit({
        "type": "agent_start",
        "agent": "analyst",
        "data": {
            "policy_type": state.policy_type,
            "mode": "agentic",
            "phases": len(ANALYST_PHASES),
        },
    })

    # Emit immediate thinking events so the UI shows activity right away
    # (graph construction + first LLM call can take several seconds)
    await emit({
        "type": "analyst_thinking",
        "agent": "analyst",
        "data": {
            "step_type": "phase_start",
            "content": f"Starting 5-phase analysis pipeline for: {state.query[:120]}",
            "phase": "0",
        },
    })
    await emit({
        "type": "analyst_thinking",
        "agent": "analyst",
        "data": {
            "step_type": "reasoning",
            "content": f"Policy type: {state.policy_type or 'general'} — initializing LangGraph agent with {len(ANALYST_PHASES)} phases",
            "phase": "0",
        },
    })

    try:
        state = await _run_langgraph_analyst(state, emit)
    except Exception as e:
        logger.warning(f"LangGraph analyst failed ({e}), falling back to simple analyst")
        await emit({
            "type": "analyst_tool_call",
            "agent": "analyst",
            "data": {"tool": "fallback", "query": f"LangGraph unavailable: {str(e)[:100]}. Using simple analyst."},
        })
        state = await _run_simple_analyst(state, emit)

    return state


# ---------------------------------------------------------------------------
# LangGraph agentic analyst (primary path)
# ---------------------------------------------------------------------------

async def _run_langgraph_analyst(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Run Rudra's 5-phase LangGraph analyst agent with SSE events per phase."""
    from backend.agents.graph import AnalystState, build_analyst_graph
    from backend.agents.schemas import AnalystBriefing, ToolCallRecord as AgentToolCallRecord

    graph = build_analyst_graph()

    initial_state: AnalystState = {
        "policy_query": state.query,
        "current_phase": 1,
        "phase_1_output": None,
        "phase_2_output": None,
        "phase_3_output": None,
        "phase_4_output": None,
        "phase_5_output": None,
        "tool_call_log": [],
    }

    # Stream through the graph to emit per-phase SSE events
    phase_start_times: dict[int, float] = {}
    current_phase = 0
    total_tool_calls = 0

    async def _think(step_type: str, content: str, phase: int, tool: str | None = None) -> None:
        """Emit a thinking event for the analyst spotlight stream."""
        await emit({
            "type": "analyst_thinking",
            "agent": "analyst",
            "data": {
                "step_type": step_type,
                "content": content,
                "phase": str(phase),
                "tool": tool,
            },
        })

    async for event in graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            new_phase = node_output.get("current_phase", current_phase)

            # Detect phase transition
            if new_phase != current_phase:
                # Complete previous phase
                if current_phase > 0 and current_phase in phase_start_times:
                    phase_duration = time.time() - phase_start_times[current_phase]
                    phase_tool_records = node_output.get("tool_call_log", [])
                    new_tool_count = len(phase_tool_records) - total_tool_calls
                    total_tool_calls = len(phase_tool_records)

                    await _think("phase_complete", f"Phase {current_phase} ({ANALYST_PHASES[current_phase]['name']}) complete — {new_tool_count} tool calls in {phase_duration:.1f}s", current_phase)

                    await emit({
                        "type": "analyst_tool_call",
                        "agent": "analyst",
                        "data": {
                            "tool": f"phase_{current_phase}_complete",
                            "query": f"Phase {current_phase} ({ANALYST_PHASES[current_phase]['name']}) complete — {new_tool_count} tool calls in {phase_duration:.1f}s",
                        },
                    })

                # Start new phase
                prev_phase = current_phase
                current_phase = new_phase
                if current_phase <= 5:
                    phase_meta = ANALYST_PHASES.get(current_phase, {})
                    phase_start_times[current_phase] = time.time()

                    await _think("phase_start", f"Phase {current_phase}/5: {phase_meta.get('name', 'Unknown')} ({phase_meta.get('type', 'unknown')})", current_phase)

                    await emit({
                        "type": "analyst_tool_call",
                        "agent": "analyst",
                        "data": {
                            "tool": f"phase_{current_phase}_start",
                            "query": f"Phase {current_phase}/5: {phase_meta.get('name', 'Unknown')} ({phase_meta.get('type', 'unknown')})",
                        },
                    })

                    if phase_meta.get("tools"):
                        await _think("reasoning", f"Tools available: {', '.join(phase_meta['tools'])}", current_phase)
                        await emit({
                            "type": "analyst_tool_call",
                            "agent": "analyst",
                            "data": {
                                "tool": "tools_available",
                                "query": f"Tools: {', '.join(phase_meta['tools'])}",
                            },
                        })

            # Extract tool call records from this node's output for SSE
            new_records = node_output.get("tool_call_log", [])
            if new_records and len(new_records) > total_tool_calls:
                for record in new_records[total_tool_calls:]:
                    if hasattr(record, "tool_name"):
                        tool_name = record.tool_name
                        tool_args = json.dumps(record.arguments)[:200] if record.arguments else ""
                        result_summary = record.result_summary[:150] if hasattr(record, "result_summary") and record.result_summary else ""

                        await _think("tool_call", f"{tool_name}({tool_args})", current_phase, tool_name)
                        if result_summary:
                            await _think("tool_result", result_summary, current_phase, tool_name)

                        await emit({
                            "type": "analyst_tool_call",
                            "agent": "analyst",
                            "data": {
                                "tool": tool_name,
                                "query": tool_args,
                            },
                        })
                total_tool_calls = len(new_records)

            # Emit reasoning content from phase summaries if available
            for summary_key in ["phase_1_summary", "phase_2_summary", "phase_3_summary"]:
                summary = node_output.get(summary_key)
                if summary and isinstance(summary, str):
                    phase_num = int(summary_key.split("_")[1])
                    await _think("reasoning", summary[:300], phase_num)

            # Check if we got the final briefing
            briefing = node_output.get("phase_5_output")
            if briefing is not None:
                # Final phase complete
                if current_phase in phase_start_times:
                    phase_duration = time.time() - phase_start_times[current_phase]
                    await _think("phase_complete", f"Phase 5 (Synthesis & Briefing) complete in {phase_duration:.1f}s", 5)
                    await emit({
                        "type": "analyst_tool_call",
                        "agent": "analyst",
                        "data": {
                            "tool": "phase_5_complete",
                            "query": f"Phase 5 (Synthesis & Briefing) complete in {phase_duration:.1f}s",
                        },
                    })

                # Convert AnalystBriefing → pipeline briefing dict
                state.briefing = _briefing_to_dict(briefing)
                state.briefing["policy_params"] = state.policy_params

                # Convert tool records
                all_records = node_output.get("tool_call_log", [])
                state.tool_calls = [
                    {
                        "tool": r.tool_name if hasattr(r, "tool_name") else str(r),
                        "args": r.arguments if hasattr(r, "arguments") else {},
                        "success": True,
                        "summary": r.result_summary[:100] if hasattr(r, "result_summary") else "",
                    }
                    for r in all_records
                ]

    # Emit analyst_complete
    tools_succeeded = len(state.tool_calls)
    summary_text = state.briefing.get("summary", state.briefing.get("executive_summary", "Analysis complete"))
    if isinstance(summary_text, str):
        summary_text = summary_text[:500]
    else:
        summary_text = "Analysis complete"

    await emit({
        "type": "analyst_complete",
        "agent": "analyst",
        "data": {
            "briefing_summary": summary_text,
            "sources_found": tools_succeeded,
            "tool_calls_made": tools_succeeded,
            "tools_called": tools_succeeded,
            "tools_succeeded": tools_succeeded,
            "summary": summary_text,
            "mode": "agentic",
            "phases_completed": 5,
        },
    })

    return state


def _briefing_to_dict(briefing: Any) -> dict[str, Any]:
    """Convert an AnalystBriefing Pydantic model to the pipeline's briefing dict."""
    if hasattr(briefing, "model_dump"):
        d = briefing.model_dump()
    elif isinstance(briefing, dict):
        d = briefing
    else:
        return {"summary": str(briefing)}

    # Flatten into the format downstream stages expect
    result: dict[str, Any] = {
        "summary": d.get("executive_summary", ""),
        "executive_summary": d.get("executive_summary", ""),
        "key_findings": d.get("key_findings", []),
        "critical_uncertainties": d.get("critical_uncertainties", []),
        "policy_spec": d.get("policy_spec"),
        "baseline": d.get("baseline"),
        "transmission_channels": d.get("transmission_channels", []),
        "evidence": d.get("evidence"),
        "sector_exposure": d.get("sector_exposure", []),
        "distributional_by_income": d.get("distributional_by_income", []),
        "distributional_by_geography": d.get("distributional_by_geography", []),
        "distributional_by_industry": d.get("distributional_by_industry", []),
        "distributional_by_firm_size": d.get("distributional_by_firm_size", []),
        "distributional_by_demographic": d.get("distributional_by_demographic", []),
        "revenue_effects": d.get("revenue_effects", ""),
        "transfer_program_effects": d.get("transfer_program_effects", ""),
        "government_cost_effects": d.get("government_cost_effects", ""),
        "key_assumptions": d.get("key_assumptions", []),
        "sensitivity_factors": d.get("sensitivity_factors", []),
        "scenarios": d.get("scenarios", {}),
        "analogous_cases": d.get("analogous_cases", []),
    }
    return result


# ---------------------------------------------------------------------------
# Simple fallback analyst (used if LangGraph is unavailable)
# ---------------------------------------------------------------------------

# Search strategies per policy type
SEARCH_STRATEGIES: dict[str, list[dict[str, Any]]] = {
    "immigration": [
        {"tool": "fred_search", "args": {"query": "H-1B visa employment"}},
        {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}},
        {"tool": "fred_get_series", "args": {"series_id": "LNS12300060"}},
        {"tool": "bls_get_data", "args": {"series_ids": ["CES0500000003"]}},
        {"tool": "search_academic_papers", "args": {"query": "H-1B visa labor market impact"}},
        {"tool": "web_search_news", "args": {"query": "H-1B visa policy 2026 changes"}},
        {"tool": "search_cbo_reports", "args": {"query": "immigration skilled workers economic impact"}},
    ],
    # Keys match PolicyTaskType enum values from backend/agents/schemas.py
    "education": [
        {"tool": "fred_search", "args": {"query": "student loan debt"}},
        {"tool": "fred_get_series", "args": {"series_id": "SLOAS"}},
        {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}},
        {"tool": "search_academic_papers", "args": {"query": "student loan forgiveness economic impact"}},
        {"tool": "web_search_news", "args": {"query": "student loan forgiveness plan 2026"}},
        {"tool": "search_cbo_reports", "args": {"query": "student loan forgiveness cost federal budget"}},
    ],
    "trade_tariff": [
        {"tool": "fred_search", "args": {"query": "tariff electronics imports China"}},
        {"tool": "fred_get_series", "args": {"series_id": "BOPGSTB"}},
        {"tool": "fred_get_series", "args": {"series_id": "PCUOMFG"}},
        {"tool": "bls_get_data", "args": {"series_ids": ["CUUR0000SA0"]}},
        {"tool": "search_academic_papers", "args": {"query": "tariff consumer prices small business impact"}},
        {"tool": "web_search_news", "args": {"query": "China electronics tariff 2026 impact"}},
    ],
    "minimum_wage": [
        {"tool": "fred_get_series", "args": {"series_id": "FEDMINNFRWG"}},  # federal minimum wage
        {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}},  # unemployment rate
        {"tool": "fred_get_series", "args": {"series_id": "LES1252881600Q"}},  # median usual weekly earnings
        {"tool": "bls_get_data", "args": {"series_ids": ["CES0500000003"]}},  # avg hourly earnings
        {"tool": "search_academic_papers", "args": {"query": "minimum wage employment effect small business"}},
        {"tool": "web_search_news", "args": {"query": "minimum wage increase 2026 economic impact"}},
        {"tool": "search_cbo_reports", "args": {"query": "minimum wage employment economic effects"}},
    ],
}

DEFAULT_STRATEGY = [
    {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}},
    {"tool": "fred_get_series", "args": {"series_id": "CPIAUCSL"}},
    {"tool": "web_search_news", "args": {"query": ""}},
]


async def _call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dynamically call a tool from backend.tools by name."""
    import backend.tools as tools_module

    tool_fn = getattr(tools_module, tool_name, None)
    if tool_fn is None:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        result = await tool_fn(**args)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result
    except Exception as e:
        return {"error": f"{tool_name} failed: {str(e)[:200]}"}


async def _run_simple_analyst(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Fallback: simple hardcoded tool calls without LangGraph."""
    strategy = SEARCH_STRATEGIES.get(state.policy_type, DEFAULT_STRATEGY)

    for step in strategy:
        if step["tool"] == "web_search_news" and not step["args"].get("query"):
            step["args"]["query"] = state.query

    briefing_data: dict[str, Any] = {}
    tool_records: list[dict[str, Any]] = []

    # Emit phase start for simple mode (single phase of data gathering)
    await emit({
        "type": "analyst_thinking",
        "agent": "analyst",
        "data": {"step_type": "phase_start", "content": "Data Gathering (simple mode — LangGraph unavailable)", "phase": "1"},
    })

    for step in strategy:
        tool_name = step["tool"]
        args = step["args"]

        await emit({
            "type": "analyst_thinking",
            "agent": "analyst",
            "data": {"step_type": "tool_call", "content": f"{tool_name}({json.dumps(args)[:120]})", "phase": "1", "tool": tool_name},
        })

        await emit({
            "type": "analyst_tool_call",
            "agent": "analyst",
            "data": {"tool": tool_name, "query": str(args)},
        })

        result = await _call_tool(tool_name, args)
        summary = _summarize_result(tool_name, result)

        tool_records.append({
            "tool": tool_name,
            "args": args,
            "success": "error" not in result,
            "summary": summary,
        })

        await emit({
            "type": "analyst_thinking",
            "agent": "analyst",
            "data": {"step_type": "tool_result", "content": summary, "phase": "1", "tool": tool_name},
        })

        briefing_data[f"{tool_name}_{len(tool_records)}"] = result

    await emit({
        "type": "analyst_thinking",
        "agent": "analyst",
        "data": {"step_type": "reasoning", "content": "Synthesizing briefing from gathered data...", "phase": "1"},
    })

    briefing_summary = await _summarize_briefing(state, briefing_data)

    await emit({
        "type": "analyst_thinking",
        "agent": "analyst",
        "data": {"step_type": "phase_complete", "content": "Briefing assembled", "phase": "1"},
    })

    state.briefing = {
        "raw_data": briefing_data,
        "summary": briefing_summary,
        "tool_calls": tool_records,
        "policy_params": state.policy_params,
    }
    state.tool_calls = tool_records

    tools_succeeded = sum(1 for t in tool_records if t["success"])
    briefing_summary_text = briefing_summary[:500] if briefing_summary else "Data gathered"

    await emit({
        "type": "analyst_complete",
        "agent": "analyst",
        "data": {
            "briefing_summary": briefing_summary_text,
            "sources_found": tools_succeeded,
            "tool_calls_made": len(tool_records),
            "tools_called": len(tool_records),
            "tools_succeeded": tools_succeeded,
            "summary": briefing_summary_text,
            "mode": "simple",
        },
    })

    return state


def _summarize_result(tool_name: str, result: dict[str, Any]) -> str:
    """One-line summary of a tool result for the SSE feed."""
    if "error" in result:
        return f"Failed: {result['error'][:100]}"
    if tool_name == "fred_get_series":
        val = result.get("latest_value", "N/A")
        title = result.get("title", "series")
        return f"{title}: {val}"
    if tool_name == "fred_search":
        count = result.get("total_results", 0)
        return f"Found {count} series"
    if tool_name.startswith("search_"):
        results = result.get("results", [])
        return f"Found {len(results)} results"
    if tool_name == "bls_get_data":
        results = result.get("results", [])
        return f"{len(results)} BLS series retrieved"
    return "Data retrieved"


ANALYST_SUMMARY_SYSTEM = """You are an economic policy analyst. Given raw data from government APIs
and academic sources, write a concise briefing summary (3-5 paragraphs) covering:
1. Current baseline conditions (key economic indicators)
2. Relevant precedents and research findings
3. Key data points that sector analysts should focus on

Be specific — cite numbers, dates, and sources. This briefing will be given to
sector analysts (labor, housing, consumer, business) for deeper analysis."""


async def _summarize_briefing(
    state: PipelineState, data: dict[str, Any]
) -> str:
    """Use LLM to synthesize raw data into a readable briefing."""
    data_str = json.dumps(data, default=str)[:8000]

    try:
        result = await llm_chat(
            system_prompt=ANALYST_SUMMARY_SYSTEM,
            user_prompt=(
                f"Policy question: {state.query}\n"
                f"Policy type: {state.policy_type}\n"
                f"Extracted parameters: {json.dumps(state.policy_params)}\n\n"
                f"Raw API data:\n{data_str}"
            ),
            temperature=0.2,
            max_tokens=2000,
        )
        return result or "Briefing data collected — LLM summary unavailable."
    except Exception:
        return "Briefing data collected — LLM summary unavailable."

"""
Stage 1: Analyst Agent — gathers baseline data from public APIs.

Uses Rudra's tools (FRED, BLS, Semantic Scholar, etc.) to build a briefing
packet, then optionally enriches it with an LLM summary.

===========================================================================
INTEGRATION GUIDE
===========================================================================
This stage calls REAL government APIs via Rudra's tools in backend/tools/.
Each tool call emits an SSE event so the frontend shows live data gathering.

If API keys are missing or calls fail, the stage gracefully degrades:
it still produces a briefing packet (possibly empty) and continues.

OWNER: Rudra — enhance with more sophisticated query planning via LLM.
Currently uses a hardcoded search strategy per policy_type.
===========================================================================
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from backend.pipeline.orchestrator import PipelineState
from backend.pipeline.llm import llm_chat, parse_json_response

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]

# ---------------------------------------------------------------------------
# Search strategies per policy type
# Maps policy_type → list of (tool_name, query/params) to execute
# ---------------------------------------------------------------------------
SEARCH_STRATEGIES: dict[str, list[dict[str, Any]]] = {
    "immigration": [
        {"tool": "fred_search", "args": {"query": "H-1B visa employment"}},
        {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}},  # unemployment rate
        {"tool": "fred_get_series", "args": {"series_id": "LNS12300060"}},  # employment-population ratio
        {"tool": "bls_get_data", "args": {"series_ids": ["CES0500000003"]}},  # avg hourly earnings
        {"tool": "search_academic_papers", "args": {"query": "H-1B visa labor market impact"}},
        {"tool": "web_search_news", "args": {"query": "H-1B visa policy 2026 changes"}},
        {"tool": "search_cbo_reports", "args": {"query": "immigration skilled workers economic impact"}},
    ],
    "education_finance": [
        {"tool": "fred_search", "args": {"query": "student loan debt"}},
        {"tool": "fred_get_series", "args": {"series_id": "SLOAS"}},  # student loans outstanding
        {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}},
        {"tool": "search_academic_papers", "args": {"query": "student loan forgiveness economic impact"}},
        {"tool": "web_search_news", "args": {"query": "student loan forgiveness plan 2026"}},
        {"tool": "search_cbo_reports", "args": {"query": "student loan forgiveness cost federal budget"}},
    ],
    "trade": [
        {"tool": "fred_search", "args": {"query": "tariff electronics imports China"}},
        {"tool": "fred_get_series", "args": {"series_id": "BOPGSTB"}},  # trade balance
        {"tool": "fred_get_series", "args": {"series_id": "PCUOMFG"}},  # PPI manufacturing
        {"tool": "bls_get_data", "args": {"series_ids": ["CUUR0000SA0"]}},  # CPI-U
        {"tool": "search_academic_papers", "args": {"query": "tariff consumer prices small business impact"}},
        {"tool": "web_search_news", "args": {"query": "China electronics tariff 2026 impact"}},
    ],
}

# Default strategy for unknown policy types
DEFAULT_STRATEGY = [
    {"tool": "fred_get_series", "args": {"series_id": "UNRATE"}},
    {"tool": "fred_get_series", "args": {"series_id": "CPIAUCSL"}},  # CPI
    {"tool": "web_search_news", "args": {"query": ""}},  # will be filled with state.query
]


async def _call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dynamically call a tool from backend.tools by name."""
    import backend.tools as tools_module

    tool_fn = getattr(tools_module, tool_name, None)
    if tool_fn is None:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        result = await tool_fn(**args)
        # Convert Pydantic model to dict
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result
    except Exception as e:
        return {"error": f"{tool_name} failed: {str(e)[:200]}"}


async def run_analyst(state: PipelineState, emit: EventCallback) -> PipelineState:
    """Stage 1: Gather baseline data from public APIs."""
    await emit({
        "type": "agent_start",
        "agent": "analyst",
        "data": {"policy_type": state.policy_type},
    })

    # Select search strategy
    strategy = SEARCH_STRATEGIES.get(state.policy_type, DEFAULT_STRATEGY)

    # Fill in any query placeholders
    for step in strategy:
        if step["tool"] == "web_search_news" and not step["args"].get("query"):
            step["args"]["query"] = state.query

    # Execute tool calls with SSE events
    briefing_data: dict[str, Any] = {}
    tool_records: list[dict[str, Any]] = []

    for step in strategy:
        tool_name = step["tool"]
        args = step["args"]

        # Emit tool call event
        await emit({
            "type": "analyst_tool_call",
            "agent": "analyst",
            "data": {"tool": tool_name, "query": str(args)},
        })

        result = await _call_tool(tool_name, args)

        tool_records.append({
            "tool": tool_name,
            "args": args,
            "success": "error" not in result,
            "summary": _summarize_result(tool_name, result),
        })

        briefing_data[f"{tool_name}_{len(tool_records)}"] = result

    # Optionally summarize briefing with LLM
    briefing_summary = await _summarize_briefing(state, briefing_data)

    state.briefing = {
        "raw_data": briefing_data,
        "summary": briefing_summary,
        "tool_calls": tool_records,
        "policy_params": state.policy_params,
    }
    state.tool_calls = tool_records

    await emit({
        "type": "analyst_complete",
        "agent": "analyst",
        "data": {
            "tools_called": len(tool_records),
            "tools_succeeded": sum(1 for t in tool_records if t["success"]),
            "summary": briefing_summary[:500] if briefing_summary else "Data gathered",
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
    import json

    # Trim data to avoid token limits
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

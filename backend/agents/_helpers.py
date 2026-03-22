"""Shared helpers for phase-gated ReAct agents.

Used by both the analyst agent and sector agents (housing, labor, etc.).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from backend.agents.llm import get_chat_model
from backend.agents.schemas import ToolCallRecord

logger = logging.getLogger(__name__)


def _extract_json_block(text) -> dict:
    """Extract JSON from a ```json ... ``` code fence, or parse the whole text.

    Handles non-string content (e.g., Gemini returns list of parts).
    """
    if not isinstance(text, str):
        if isinstance(text, list):
            parts = []
            for part in text:
                if isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
                elif isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(str(part))
            text = "\n".join(parts)
        else:
            text = str(text)

    # Try fenced JSON first
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        if extracted:
            return _parse_json_lenient(extracted)
    # Try unfenced — find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return _parse_json_lenient(text[start : end + 1])
    raise ValueError(f"No JSON found in LLM output: {text[:300]}...")


def _parse_json_lenient(text: str) -> dict:
    """Parse JSON with fixes for common LLM mistakes (trailing commas, etc)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fix trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    # Fix unquoted None/null values
    fixed = fixed.replace(": None", ": null").replace(":None", ":null")
    return json.loads(fixed)


def _extract_tool_records(messages: list, phase: int) -> list[ToolCallRecord]:
    """Walk message history and extract tool call audit records."""
    records: list[ToolCallRecord] = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                records.append(
                    ToolCallRecord(
                        phase=phase,
                        tool_name=tc["name"],
                        arguments=tc.get("args", {}),
                        result_summary="",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
        if hasattr(msg, "type") and msg.type == "tool" and records:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            records[-1].result_summary = content[:200]
    return records


async def _run_react_phase(
    system_prompt: str,
    user_message: str,
    tools: list,
    phase_num: int,
    state: dict,
    recursion_limit: int = 40,
) -> tuple[dict, list[ToolCallRecord]]:
    """Run a ReAct agent for a tool-using phase. Returns (parsed_json, tool_records)."""
    llm = get_chat_model()

    logger.info(f"Phase {phase_num} prompt size: {len(system_prompt)} chars (~{len(system_prompt)//4} tokens), tools: {[t.name for t in tools]}")

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": recursion_limit},
    )

    # Log message count for debugging
    logger.info(f"Phase {phase_num} message count: {len(result['messages'])}")

    final_msg = result["messages"][-1]
    final_content = final_msg.content
    logger.info(f"Phase {phase_num} final message type: {type(final_content).__name__}")
    logger.info(f"Phase {phase_num} final content preview: {str(final_content)[:500]}")

    tool_records = _extract_tool_records(result["messages"], phase_num)

    try:
        parsed = _extract_json_block(final_content)
        return parsed, tool_records
    except (ValueError, json.JSONDecodeError):
        pass

    # Fallback: re-prompt for structured output
    logger.warning(
        f"Phase {phase_num}: No JSON in final message. Re-prompting for structured output."
    )
    followup = await llm.ainvoke(
        result["messages"]
        + [
            HumanMessage(
                content="You ran out of steps. Based on all the data you've gathered above, "
                "produce your final output NOW as a JSON object inside a ```json code fence. "
                "Do NOT call any more tools."
            )
        ]
    )
    parsed = _extract_json_block(followup.content)
    return parsed, tool_records


def summarize_phase_output(phase_name: str, output_json: str) -> str:
    """Programmatically compress a phase output — no LLM call needed.

    Extracts key fields from JSON, preserving numbers and findings,
    discarding verbose structure. ~0ms vs ~7s for LLM summarization.
    """
    import json as _json

    try:
        data = _json.loads(output_json)
    except (ValueError, TypeError):
        # If not valid JSON, truncate the raw text
        return output_json[:2000]

    lines = [f"[{phase_name}]"]

    # Walk the dict and extract key-value pairs with numbers or short strings
    def _extract(obj, prefix="", depth=0):
        if depth > 3:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (int, float)):
                    lines.append(f"{prefix}{k}: {v}")
                elif isinstance(v, str) and len(v) < 200 and v:
                    lines.append(f"{prefix}{k}: {v}")
                elif isinstance(v, list) and len(v) <= 5 and all(isinstance(x, str) for x in v):
                    lines.append(f"{prefix}{k}: {', '.join(v[:5])}")
                elif isinstance(v, (dict, list)):
                    _extract(v, prefix=f"{prefix}{k}.", depth=depth + 1)
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:8]):
                if isinstance(item, dict):
                    # Extract the most identifying fields
                    name = item.get("name") or item.get("metric_name") or item.get("region") or item.get("region_name") or item.get("pathway_id") or ""
                    value = item.get("value") or item.get("central_estimate") or item.get("latest_value") or ""
                    extra = item.get("trend") or item.get("confidence") or item.get("relevance") or item.get("verdict") or ""
                    if name or value:
                        lines.append(f"{prefix}[{i}] {name}: {value} {extra}".strip())
                elif isinstance(item, str) and len(item) < 150:
                    lines.append(f"{prefix}[{i}] {item}")

    _extract(data)

    result = "\n".join(lines[:60])  # Cap at 60 lines
    logger.info(f"Summarized {phase_name}: {len(output_json)} chars → {len(result)} chars (programmatic)")
    return result


async def _run_reasoning_phase(
    system_prompt: str,
    user_message: str,
) -> dict:
    """Run a single LLM call for a no-tool phase. Returns parsed JSON dict."""
    llm = get_chat_model()

    response = await llm.ainvoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
    )

    return _extract_json_block(response.content)

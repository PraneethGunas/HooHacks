"""Phase node implementations for the analyst agent.

Each function takes the graph state dict and returns a partial state update.
- Tool phases (1, 2, 4): use create_react_agent for ReAct loop
- No-tool phases (3, 5): single LLM invocation
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from backend.agents.llm import get_chat_model
from backend.agents.prompts import (
    phase_1_system_prompt,
    phase_2_system_prompt,
    phase_3_system_prompt,
    phase_4_system_prompt,
    phase_5_system_prompt,
)
from backend.agents.schemas import (
    AnalystBriefing,
    BaselineOutput,
    EvidenceOutput,
    PolicySpec,
    ToolCallRecord,
    TransmissionMapOutput,
)
from backend.agents.tool_wrappers import PHASE_1_TOOLS, PHASE_2_TOOLS, PHASE_4_TOOLS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json_block(text) -> dict:
    """Extract JSON from a ```json ... ``` code fence, or parse the whole text.

    Handles non-string content (e.g., Gemini returns list of parts).
    """
    # Ensure we have a string — handle Gemini's list-of-parts format
    if not isinstance(text, str):
        if isinstance(text, list):
            # Gemini returns [{'type': 'text', 'text': '...'}, ...]
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
            return json.loads(extracted)
        # Empty code fence — fall through to unfenced search
    # Try unfenced — find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])
    raise ValueError(f"No JSON found in LLM output: {text[:300]}...")


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

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": recursion_limit},
    )

    final_msg = result["messages"][-1]
    final_content = final_msg.content
    logger.info(f"Phase {phase_num} final message type: {type(final_content).__name__}")
    logger.info(f"Phase {phase_num} final content preview: {str(final_content)[:500]}")

    tool_records = _extract_tool_records(result["messages"], phase_num)

    # Try to extract JSON from the final message
    try:
        parsed = _extract_json_block(final_content)
        return parsed, tool_records
    except (ValueError, json.JSONDecodeError):
        pass

    # Fallback: LLM hit recursion limit without producing JSON.
    # Re-prompt with all context asking it to produce the structured output now.
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


# ---------------------------------------------------------------------------
# Phase Nodes
# ---------------------------------------------------------------------------


async def phase_1_policy_spec(state: dict) -> dict:
    """Phase 1: Policy Specification — ReAct with web search, doc fetch, FRED."""
    logger.info("=== PHASE 1: Policy Specification ===")
    policy_query = state["policy_query"]
    prompt = phase_1_system_prompt(policy_query)

    parsed, tool_records = await _run_react_phase(
        system_prompt=prompt,
        user_message=f"Analyze this policy proposal: {policy_query}",
        tools=PHASE_1_TOOLS,
        phase_num=1,
        state=state,
    )

    policy_spec = PolicySpec(**parsed)
    logger.info(f"Phase 1 complete: {policy_spec.action} — {policy_spec.value}")

    return {
        "current_phase": 2,
        "phase_1_output": policy_spec,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def phase_2_baseline(state: dict) -> dict:
    """Phase 2: Baseline & Counterfactual — ReAct with FRED + BLS."""
    logger.info("=== PHASE 2: Baseline & Counterfactual ===")
    prompt = phase_2_system_prompt(state["policy_query"], state["phase_1_output"])

    parsed, tool_records = await _run_react_phase(
        system_prompt=prompt,
        user_message="Construct the baseline and counterfactual for this policy.",
        tools=PHASE_2_TOOLS,
        phase_num=2,
        state=state,
    )

    baseline = BaselineOutput(**parsed)
    logger.info(f"Phase 2 complete: {len(baseline.key_metrics)} metrics gathered")

    return {
        "current_phase": 3,
        "phase_2_output": baseline,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def phase_3_transmission(state: dict) -> dict:
    """Phase 3: Transmission Channel Mapping — No tools, pure reasoning."""
    logger.info("=== PHASE 3: Transmission Channel Mapping ===")
    prompt = phase_3_system_prompt(
        state["policy_query"], state["phase_1_output"], state["phase_2_output"]
    )

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Map all transmission channels for this policy based on the data gathered.",
    )

    transmission_map = TransmissionMapOutput(**parsed)
    logger.info(f"Phase 3 complete: {len(transmission_map.channels)} channels identified")

    return {
        "current_phase": 4,
        "phase_3_output": transmission_map,
    }


async def phase_4_evidence(state: dict) -> dict:
    """Phase 4: Evidence Gathering — ReAct with academic search + CBO + news."""
    logger.info("=== PHASE 4: Evidence Gathering ===")
    prompt = phase_4_system_prompt(
        state["policy_query"],
        state["phase_1_output"],
        state["phase_2_output"],
        state["phase_3_output"],
    )

    parsed, tool_records = await _run_react_phase(
        system_prompt=prompt,
        user_message="Gather empirical evidence for each transmission channel.",
        tools=PHASE_4_TOOLS,
        phase_num=4,
        state=state,
        recursion_limit=60,  # Phase 4 makes the most tool calls
    )

    evidence = EvidenceOutput(**parsed)
    logger.info(
        f"Phase 4 complete: evidence for {len(evidence.evidence_by_channel)} channels"
    )

    return {
        "current_phase": 5,
        "phase_4_output": evidence,
        "tool_call_log": state.get("tool_call_log", []) + tool_records,
    }


async def phase_5_synthesis(state: dict) -> dict:
    """Phase 5: Synthesis & Briefing — No tools, produces final AnalystBriefing."""
    logger.info("=== PHASE 5: Synthesis & Briefing ===")
    prompt = phase_5_system_prompt(
        state["policy_query"],
        state["phase_1_output"],
        state["phase_2_output"],
        state["phase_3_output"],
        state["phase_4_output"],
    )

    parsed = await _run_reasoning_phase(
        system_prompt=prompt,
        user_message="Produce the final analyst briefing.",
    )

    # Inject prior phase data into the briefing if the LLM didn't include it
    if "policy_spec" not in parsed or parsed["policy_spec"] is None:
        parsed["policy_spec"] = state["phase_1_output"].model_dump()
    if "baseline" not in parsed or parsed["baseline"] is None:
        parsed["baseline"] = state["phase_2_output"].model_dump()
    if "transmission_channels" not in parsed or not parsed["transmission_channels"]:
        parsed["transmission_channels"] = [
            c.model_dump() for c in state["phase_3_output"].channels
        ]
    if "evidence" not in parsed or parsed["evidence"] is None:
        parsed["evidence"] = state["phase_4_output"].model_dump()

    briefing = AnalystBriefing(**parsed)
    logger.info("Phase 5 complete: Analyst briefing produced")

    return {
        "current_phase": 5,
        "phase_5_output": briefing,
    }

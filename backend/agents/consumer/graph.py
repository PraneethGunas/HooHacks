"""LangGraph StateGraph for the Consumer & Prices sector agent.

Uses a conditional edge after Phase 1: if no price shock entry points
are HIGH or MEDIUM relevance, skips to a minimal report.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from backend.agents.consumer.nodes import (
    consumer_phase_1_shock,
    consumer_phase_2_passthrough,
    consumer_phase_3_geo_behavioral,
    consumer_phase_4_purchasing_power,
    consumer_phase_5_scorecard,
    consumer_phase_5_minimal,
)
from backend.agents.consumer.schemas import ConsumerState

logger = logging.getLogger(__name__)


def _should_continue(state: dict) -> str:
    """Check Phase 1 output — skip to minimal report if no relevant entry points."""
    p1 = state.get("phase_1_output")
    if not p1 or not p1.entry_points:
        logger.info("Consumer: No Phase 1 output — skipping to minimal report")
        return "phase_5_minimal"

    relevant = [
        e for e in p1.entry_points
        if e.relevance.upper() in ("HIGH", "MEDIUM")
    ]

    if not relevant:
        logger.info("Consumer: No HIGH/MEDIUM entry points — skipping to minimal report")
        return "phase_5_minimal"

    logger.info(f"Consumer: {len(relevant)} relevant entry points — proceeding with full analysis")
    return "phase_2_passthrough"


def build_consumer_graph():
    """Build and compile the consumer agent graph with conditional early exit."""
    graph = StateGraph(ConsumerState)

    graph.add_node("phase_1_shock", consumer_phase_1_shock)
    graph.add_node("phase_2_passthrough", consumer_phase_2_passthrough)
    graph.add_node("phase_3_geo_behavioral", consumer_phase_3_geo_behavioral)
    graph.add_node("phase_4_purchasing_power", consumer_phase_4_purchasing_power)
    graph.add_node("phase_5_scorecard", consumer_phase_5_scorecard)
    graph.add_node("phase_5_minimal", consumer_phase_5_minimal)

    graph.add_edge(START, "phase_1_shock")
    graph.add_conditional_edges("phase_1_shock", _should_continue)
    graph.add_edge("phase_2_passthrough", "phase_3_geo_behavioral")
    graph.add_edge("phase_3_geo_behavioral", "phase_4_purchasing_power")
    graph.add_edge("phase_4_purchasing_power", "phase_5_scorecard")
    graph.add_edge("phase_5_scorecard", END)
    graph.add_edge("phase_5_minimal", END)

    return graph.compile()

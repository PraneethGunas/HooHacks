"""LangGraph StateGraph for the Housing & Cost of Living sector agent.

Uses a conditional edge after Phase 1: if no pathways are HIGH or MEDIUM
relevance, skips directly to a minimal report (saves ~300s).
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from backend.agents.housing.nodes import (
    housing_phase_1_pathways,
    housing_phase_2_baseline,
    housing_phase_3_magnitudes,
    housing_phase_4_distributional,
    housing_phase_5_scorecard,
    housing_phase_5_minimal,
)
from backend.agents.housing.schemas import HousingState

logger = logging.getLogger(__name__)


def _should_continue(state: dict) -> str:
    """Check Phase 1 output — skip to minimal report if no relevant pathways."""
    p1 = state.get("phase_1_output")
    if not p1 or not p1.pathways:
        logger.info("Housing: No Phase 1 output — skipping to minimal report")
        return "phase_5_minimal"

    relevant = [
        p for p in p1.pathways
        if p.relevance.upper() in ("HIGH", "MEDIUM")
    ]

    if not relevant:
        logger.info(f"Housing: No HIGH/MEDIUM pathways — skipping to minimal report")
        return "phase_5_minimal"

    logger.info(f"Housing: {len(relevant)} relevant pathways — proceeding with full analysis")
    return "phase_2_baseline"


def build_housing_graph():
    """Build and compile the housing agent graph with conditional early exit."""
    graph = StateGraph(HousingState)

    graph.add_node("phase_1_pathways", housing_phase_1_pathways)
    graph.add_node("phase_2_baseline", housing_phase_2_baseline)
    graph.add_node("phase_3_magnitudes", housing_phase_3_magnitudes)
    graph.add_node("phase_4_distributional", housing_phase_4_distributional)
    graph.add_node("phase_5_scorecard", housing_phase_5_scorecard)
    graph.add_node("phase_5_minimal", housing_phase_5_minimal)

    graph.add_edge(START, "phase_1_pathways")
    graph.add_conditional_edges("phase_1_pathways", _should_continue)
    graph.add_edge("phase_2_baseline", "phase_3_magnitudes")
    graph.add_edge("phase_3_magnitudes", "phase_4_distributional")
    graph.add_edge("phase_4_distributional", "phase_5_scorecard")
    graph.add_edge("phase_5_scorecard", END)
    graph.add_edge("phase_5_minimal", END)

    return graph.compile()

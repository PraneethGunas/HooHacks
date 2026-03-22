"""LangGraph StateGraph for the Housing & Cost of Living sector agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.agents.housing.nodes import (
    housing_phase_1_pathways,
    housing_phase_2_baseline,
    housing_phase_3_magnitudes,
    housing_phase_4_distributional,
    housing_phase_5_scorecard,
)
from backend.agents.housing.schemas import HousingState


def build_housing_graph():
    """Build and compile the 5-phase housing agent graph."""
    graph = StateGraph(HousingState)

    graph.add_node("phase_1_pathways", housing_phase_1_pathways)
    graph.add_node("phase_2_baseline", housing_phase_2_baseline)
    graph.add_node("phase_3_magnitudes", housing_phase_3_magnitudes)
    graph.add_node("phase_4_distributional", housing_phase_4_distributional)
    graph.add_node("phase_5_scorecard", housing_phase_5_scorecard)

    graph.add_edge(START, "phase_1_pathways")
    graph.add_edge("phase_1_pathways", "phase_2_baseline")
    graph.add_edge("phase_2_baseline", "phase_3_magnitudes")
    graph.add_edge("phase_3_magnitudes", "phase_4_distributional")
    graph.add_edge("phase_4_distributional", "phase_5_scorecard")
    graph.add_edge("phase_5_scorecard", END)

    return graph.compile()

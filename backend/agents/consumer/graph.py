"""LangGraph StateGraph for the Consumer & Prices sector agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.agents.consumer.nodes import (
    consumer_phase_1_shock,
    consumer_phase_2_passthrough,
    consumer_phase_3_geo_behavioral,
    consumer_phase_4_purchasing_power,
    consumer_phase_5_scorecard,
)
from backend.agents.consumer.schemas import ConsumerState


def build_consumer_graph():
    """Build and compile the 5-phase consumer agent graph."""
    graph = StateGraph(ConsumerState)

    graph.add_node("phase_1_shock", consumer_phase_1_shock)
    graph.add_node("phase_2_passthrough", consumer_phase_2_passthrough)
    graph.add_node("phase_3_geo_behavioral", consumer_phase_3_geo_behavioral)
    graph.add_node("phase_4_purchasing_power", consumer_phase_4_purchasing_power)
    graph.add_node("phase_5_scorecard", consumer_phase_5_scorecard)

    graph.add_edge(START, "phase_1_shock")
    graph.add_edge("phase_1_shock", "phase_2_passthrough")
    graph.add_edge("phase_2_passthrough", "phase_3_geo_behavioral")
    graph.add_edge("phase_3_geo_behavioral", "phase_4_purchasing_power")
    graph.add_edge("phase_4_purchasing_power", "phase_5_scorecard")
    graph.add_edge("phase_5_scorecard", END)

    return graph.compile()

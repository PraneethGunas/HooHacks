"""LangGraph StateGraph for the Synthesis & Impact Dashboard agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.agents.synthesis.nodes import (
    synthesis_phase_1_audit,
    synthesis_phase_2_impact,
    synthesis_phase_3_winners,
    synthesis_phase_4_narrative,
    synthesis_phase_5_payload,
)
from backend.agents.synthesis.schemas import SynthesisState


def build_synthesis_graph():
    """Build and compile the 5-phase synthesis agent graph."""
    graph = StateGraph(SynthesisState)

    graph.add_node("phase_1_audit", synthesis_phase_1_audit)
    graph.add_node("phase_2_impact", synthesis_phase_2_impact)
    graph.add_node("phase_3_winners", synthesis_phase_3_winners)
    graph.add_node("phase_4_narrative", synthesis_phase_4_narrative)
    graph.add_node("phase_5_payload", synthesis_phase_5_payload)

    graph.add_edge(START, "phase_1_audit")
    graph.add_edge("phase_1_audit", "phase_2_impact")
    graph.add_edge("phase_2_impact", "phase_3_winners")
    graph.add_edge("phase_3_winners", "phase_4_narrative")
    graph.add_edge("phase_4_narrative", "phase_5_payload")
    graph.add_edge("phase_5_payload", END)

    return graph.compile()

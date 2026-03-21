"""LangGraph StateGraph for the 5-phase analyst agent.

Linear pipeline: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
"""

from __future__ import annotations

from typing import Annotated

from langgraph.graph import StateGraph, START, END

from backend.agents.nodes import (
    phase_1_policy_spec,
    phase_2_baseline,
    phase_3_transmission,
    phase_4_evidence,
    phase_5_synthesis,
)
from backend.agents.schemas import (
    AnalystBriefing,
    BaselineOutput,
    EvidenceOutput,
    PolicySpec,
    ToolCallRecord,
    TransmissionMapOutput,
)


# ---------------------------------------------------------------------------
# Graph state — TypedDict for LangGraph
# ---------------------------------------------------------------------------

from typing import TypedDict


class AnalystState(TypedDict, total=False):
    """State that flows through the analyst agent graph."""
    # Input
    policy_query: str

    # Phase tracking
    current_phase: int

    # Phase outputs (populated as each phase completes)
    phase_1_output: PolicySpec | None
    phase_2_output: BaselineOutput | None
    phase_3_output: TransmissionMapOutput | None
    phase_4_output: EvidenceOutput | None
    phase_5_output: AnalystBriefing | None

    # Audit trail
    tool_call_log: list[ToolCallRecord]


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_analyst_graph():
    """Build and compile the 5-phase analyst agent graph."""
    graph = StateGraph(AnalystState)

    # Add phase nodes
    graph.add_node("phase_1_policy_spec", phase_1_policy_spec)
    graph.add_node("phase_2_baseline", phase_2_baseline)
    graph.add_node("phase_3_transmission", phase_3_transmission)
    graph.add_node("phase_4_evidence", phase_4_evidence)
    graph.add_node("phase_5_synthesis", phase_5_synthesis)

    # Linear sequence
    graph.add_edge(START, "phase_1_policy_spec")
    graph.add_edge("phase_1_policy_spec", "phase_2_baseline")
    graph.add_edge("phase_2_baseline", "phase_3_transmission")
    graph.add_edge("phase_3_transmission", "phase_4_evidence")
    graph.add_edge("phase_4_evidence", "phase_5_synthesis")
    graph.add_edge("phase_5_synthesis", END)

    return graph.compile()

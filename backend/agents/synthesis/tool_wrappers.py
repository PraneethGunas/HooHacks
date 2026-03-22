from __future__ import annotations

from backend.agents.housing.tool_wrappers import code_execute

# Synthesis agent only uses code_execute — no external API tools
SYNTHESIS_PHASE_1_TOOLS = []       # Reasoning only
SYNTHESIS_PHASE_2_TOOLS = [code_execute]  # Net impact computation
SYNTHESIS_PHASE_3_TOOLS = [code_execute]  # Winners/losers computation
SYNTHESIS_PHASE_4_TOOLS = []       # Narrative reasoning only
SYNTHESIS_PHASE_5_TOOLS = [code_execute]  # Payload structuring

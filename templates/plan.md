# Plan: Phase-Gated ReAct Analyst Agent

## Context

The 8 data-fetching tools are built and tested. Now we build the Analyst Agent — the first agent in the PolicyPulse pipeline. It follows the strict 5-phase workflow from `templates/policyanalyst-framework.txt`. We enforce the phase sequence in LangGraph (5 nodes, linear graph), but within each phase the LLM has full tool autonomy (ReAct). Phases 3 and 5 have zero tools — enforced structurally.

LLM: **Gemini** (`gemini-2.0-flash` via `langchain-google-genai`).

## Architecture: Phase-Gated ReAct

```
Phase 1: POLICY SPEC       [ReAct: web_search_news, fetch_document_text, fred_get_series]
    ↓ PolicySpec (structured JSON)
Phase 2: BASELINE DATA      [ReAct: fred_search, fred_get_series, bls_get_data]
    ↓ BaselineOutput
Phase 3: TRANSMISSION MAP   [No tools — single LLM call, pure reasoning]
    ↓ TransmissionMapOutput
Phase 4: EVIDENCE           [ReAct: search_academic_papers, search_openalex, search_cbo_reports, fetch_document_text, web_search_news]
    ↓ EvidenceOutput
Phase 5: SYNTHESIS           [No tools — single LLM call, produces final briefing]
    ↓ AnalystBriefing
```

Each phase:
- Gets a phase-specific system prompt (from framework.txt) + all prior phase outputs as JSON context
- Must produce structured Pydantic output before advancing
- ReAct phases use `create_react_agent` with scoped tool sets
- No-tool phases are single `llm.ainvoke()` calls
- Messages are cleared between phases (context carries via serialized prior outputs, not message history)

## New Files

```
backend/agents/
├── __init__.py          # re-exports build_analyst_graph, run_analyst_agent, AnalystBriefing
├── schemas.py           # Phase output models, AnalystBriefing, AnalystState TypedDict, ToolCallRecord
├── llm.py               # get_chat_model() factory — Gemini default, swappable via env
├── tool_wrappers.py     # Wraps async tools → LangChain @tool (JSON string returns) + PHASE_X_TOOLS lists
├── prompts.py           # System prompts per phase — derived from framework.txt
├── nodes.py             # Phase node functions (phase_1_policy_spec ... phase_5_synthesis)
├── graph.py             # LangGraph StateGraph: 5 nodes, linear edges, compile
└── run.py               # CLI entry point: run_analyst_agent("Raise min wage to $15")

tests/
└── test_analyst_agent.py  # Integration test on minimum wage query
```

## Modified Files

- `requirements.txt` — add langgraph, langchain-core, langchain-google-genai
- `backend/config.py` — add GEMINI_API_KEY, LLM_PROVIDER, LLM_MODEL_NAME fields
- `.env` — user adds GEMINI_API_KEY
- `.env.example` — add LLM env vars

## Key Schemas

**Phase outputs** (each is a Pydantic BaseModel):

| Phase | Model | Key Fields |
|-------|-------|-----------|
| 1 | `PolicySpec` | action, value, scope, timeline, exemptions, enforcement, current_baseline, ambiguities, working_assumptions |
| 2 | `BaselineOutput` | key_metrics (list of data points with series_id + source), existing_trends, scheduled_changes, policy_bite (by segment), counterfactual_summary |
| 3 | `TransmissionMapOutput` | channels (list of TransmissionChannel: name, mechanism, who_affected, direction, magnitude_estimate, confidence, empirically_studied) |
| 4 | `EvidenceOutput` | evidence_by_channel (dict mapping channel→evidence items), literature_consensus, literature_disputes, evidence_gaps |
| 5 | `AnalystBriefing` | executive_summary, key_findings, policy_spec, baseline, transmission_channels, distributional analysis (by income/geo/industry/firm_size/demographic), fiscal_impact, sector_exposure matrix, evidence, uncertainties, analogous_cases |

**Graph state** (`AnalystState` TypedDict):
- `policy_query: str` — raw user input
- `current_phase: int` — tracks progress (1-5)
- `messages: list[BaseMessage]` — per-phase ReAct messages, cleared between phases
- `phase_1_output` through `phase_5_output` — populated as phases complete
- `tool_call_log: list[ToolCallRecord]` — full audit trail

## Tool Wrapping Pattern

Existing async tools return Pydantic models. LangChain tools need string returns. Wrapper pattern:

```python
@tool
async def fred_search(query: str, limit: int = 5) -> str:
    """Search FRED for economic data series by keyword."""
    result = await _fred_search(query=query, limit=limit)
    return result.model_dump_json(indent=2)
```

Phase-to-tool mapping constants:
- `PHASE_1_TOOLS = [web_search_news, fetch_document_text, fred_get_series]`
- `PHASE_2_TOOLS = [fred_search, fred_get_series, bls_get_data]`
- `PHASE_3_TOOLS = []`
- `PHASE_4_TOOLS = [search_academic_papers, search_openalex, search_cbo_reports, fetch_document_text, web_search_news]`
- `PHASE_5_TOOLS = []`

## System Prompts (prompts.py)

Each phase prompt = CORE_IDENTITY (framework principles) + phase-specific instructions (from framework.txt) + prior phase outputs as JSON + output schema instruction.

- Prior phase outputs are serialized via `model.model_dump_json()` and injected into the prompt
- LLM is asked to produce JSON in a ```json code fence
- `_extract_json_block()` helper parses it, Pydantic validates it

## Graph (graph.py)

Linear StateGraph — 5 nodes, unconditional edges:
```
START → phase_1 → phase_2 → phase_3 → phase_4 → phase_5 → END
```

## Node Pattern (nodes.py)

**Tool phases (1, 2, 4):**
```python
async def phase_X(state):
    llm = get_chat_model()
    prompt = phase_X_system_prompt(state["policy_query"], ...prior outputs...)
    react_agent = create_react_agent(model=llm, tools=PHASE_X_TOOLS, prompt=prompt)
    result = await react_agent.ainvoke({"messages": [HumanMessage(...)]})
    parsed = _extract_json_block(result["messages"][-1].content)
    output = PhaseXModel(**parsed)
    return {"phase_X_output": output, "current_phase": X+1, ...}
```

**No-tool phases (3, 5):**
```python
async def phase_X(state):
    llm = get_chat_model()
    prompt = phase_X_system_prompt(...)
    response = await llm.ainvoke([SystemMessage(prompt), HumanMessage(...)])
    parsed = _extract_json_block(response.content)
    output = PhaseXModel(**parsed)
    return {"phase_X_output": output, ...}
```

## Implementation Order

1. `requirements.txt` — add deps, `pip install`
2. `backend/config.py` — add LLM settings
3. `.env.example` — add LLM env vars
4. `backend/agents/schemas.py` — all models + state (no LangGraph dependency)
5. `backend/agents/llm.py` — model factory
6. `backend/agents/tool_wrappers.py` — wrappers + phase tool lists
7. `backend/agents/prompts.py` — system prompts from framework
8. `backend/agents/nodes.py` — phase implementations
9. `backend/agents/graph.py` — graph assembly
10. `backend/agents/run.py` — CLI runner
11. `backend/agents/__init__.py` — re-exports
12. `tests/test_analyst_agent.py` — integration test

## Verification

```bash
# Install new deps
pip install -r requirements.txt

# Run the agent on minimum wage query
python -m backend.agents.run "Raise the federal minimum wage to $15/hr"

# Integration test
python -m pytest tests/test_analyst_agent.py -v -s --timeout=120
```

## Risks & Mitigations

- **JSON parsing failures:** LLM may not produce clean JSON. Mitigation: `_extract_json_block` handles fenced/unfenced JSON. Add 1-retry with validation error feedback.
- **ReAct loop divergence:** LLM may call tools indefinitely. Mitigation: `recursion_limit=15` on `create_react_agent`.
- **Gemini system message quirk:** Gemini converts system messages to human. Mitigation: `convert_system_message_to_human=True` in model config, keep prompts concise.
- **Token growth by Phase 5:** Accumulated context from all prior phases. Mitigation: Phase 2 output uses summary fields, not raw observation arrays.
- **`create_react_agent` API:** May differ across langgraph versions. Verify `prompt` parameter support after install.

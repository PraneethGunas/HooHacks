"""
Stage 0: Policy Classifier — powered by Google ADK (SZNS Solutions sponsor track).

===========================================================================
INTEGRATION GUIDE
===========================================================================

STATUS: 🟢 IMPLEMENTED — ADK Classifier sits at the top of the pipeline.

WHAT IT DOES:
  Receives the raw user query ("Raise the federal minimum wage to $15/hr")
  and uses Google's Agent Development Kit (ADK) with a cheap/fast Gemini
  Flash model to:
    1. Identify the policy category (task_type)
    2. Extract structured parameters (action, value, scope, timeline, …)
    3. Normalise the query for the downstream LangGraph pipeline
    4. Return a ClassifierOutput Pydantic model

WHY ADK HERE:
  - Stage 0 is deliberately cheap/fast — Gemini Flash via ADK, not the
    heavier Gemini Pro used by the analyst/sector agents.
  - ADK's Agent abstraction + InMemorySessionService is a natural fit for
    a stateless, single-turn classification step.
  - No tool calls needed — pure reasoning/extraction, which is where ADK
    single-agent mode shines.

HOW TO WIRE INTO THE PIPELINE (main.py / api/query.py):
  from backend.agents.classifier import run_classifier

  # Before kicking off the LangGraph analyst graph:
  classifier_output = await run_classifier(user_query)
  # classifier_output.task_type  → routes to appropriate sector emphasis
  # classifier_output.policy_params → fed into AnalystState.policy_query
  # classifier_output.cleaned_query → use this as the canonical query

REQUIREMENTS:
  - google-adk>=0.3.0  (pip install google-adk)
  - GOOGLE_API_KEY (or GEMINI_API_KEY) set in .env
  - llm_provider = "gemini" recommended; falls back gracefully otherwise.

OWNER: Rudra (agent orchestration)
===========================================================================
"""

from __future__ import annotations

import json
import re
import uuid
from functools import lru_cache

from backend.agents.schemas import ClassifierOutput, PolicyTaskType
from backend.config import settings

# ---------------------------------------------------------------------------
# Classifier prompt
# ---------------------------------------------------------------------------

_CLASSIFIER_INSTRUCTION = """
You are a policy classification engine for an economic policy simulation system.

Given a user's raw policy proposal, you must extract and return a JSON object
with EXACTLY these fields:

{
  "task_type": "<one of: minimum_wage, trade_tariff, immigration, tax_policy, housing_regulation, healthcare, education, environmental, other>",
  "policy_params": {
    "action":   "<what the policy does, e.g. 'Raise the federal minimum wage'>",
    "value":    "<specific magnitude/value, e.g. '$15 per hour'>",
    "scope":    "<geographic or demographic scope, e.g. 'Federal, all employers'>",
    "timeline": "<implementation timeline if mentioned, else 'unspecified'>"
  },
  "confidence": "<high | medium | low>",
  "cleaned_query": "<a clear, unambiguous restatement of the user's policy proposal>",
  "reasoning": "<one sentence: why you chose this task_type>"
}

Rules:
- confidence = "high"   if all four policy_params fields are clearly present.
- confidence = "medium" if 2-3 fields are clear, rest are inferable.
- confidence = "low"    if the proposal is vague or incomplete.
- cleaned_query must be a complete, grammatically correct policy statement.
- Return ONLY the JSON block wrapped in ```json ... ``` fences. No other text.
"""

# ---------------------------------------------------------------------------
# ADK agent + runner (module-level singletons)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_agent_and_runner():
    """
    Lazily build the ADK Agent and Runner.
    Deferred import so the rest of the backend works even if google-adk
    is not installed (unit tests, non-Gemini providers, etc.).
    """
    import os
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    # ADK reads GOOGLE_API_KEY from the environment automatically.
    api_key = settings.gemini_api_key or settings.google_api_key
    if api_key:
        os.environ.setdefault("GOOGLE_API_KEY", api_key)

    agent = Agent(
        name="policy_classifier",
        model=settings.classifier_model_name,  # gemini-3-flash-preview
        instruction=_CLASSIFIER_INSTRUCTION,
    )

    session_service = InMemorySessionService()

    runner = Runner(
        agent=agent,
        app_name="policypulse_classifier",
        session_service=session_service,
    )

    return runner, session_service


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_classifier(policy_query: str) -> ClassifierOutput:
    """
    Classify a raw policy query using the Google ADK agent.

    Returns a ClassifierOutput containing:
      - task_type      : detected policy category
      - policy_params  : extracted parameters (action, value, scope, timeline)
      - confidence     : high | medium | low
      - cleaned_query  : normalised query ready for the LangGraph pipeline
      - reasoning      : brief explanation of the classification

    Falls back gracefully to a minimal ClassifierOutput if ADK is
    unavailable or the response cannot be parsed.
    """
    try:
        return await _run_adk_classifier(policy_query)
    except ImportError:
        # google-adk not installed — return a passthrough so the rest of the
        # pipeline isn't blocked.
        return ClassifierOutput(
            task_type=PolicyTaskType.OTHER,
            policy_params={},
            confidence="low",
            cleaned_query=policy_query,
            reasoning="google-adk not installed; classifier skipped.",
        )
    except Exception as exc:  # noqa: BLE001
        # ADK call failed (network, quota, etc.) — degrade gracefully.
        return ClassifierOutput(
            task_type=PolicyTaskType.OTHER,
            policy_params={},
            confidence="low",
            cleaned_query=policy_query,
            reasoning=f"Classifier error: {exc}",
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _run_adk_classifier(policy_query: str) -> ClassifierOutput:
    """Run the ADK agent and return a parsed ClassifierOutput."""
    from google.genai import types

    runner, session_service = _build_agent_and_runner()

    # Each classification gets its own ephemeral session.
    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name="policypulse_classifier",
        user_id="system",
        session_id=session_id,
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="system",
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=policy_query)],
        ),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text
            break

    return _parse_response(response_text, policy_query)


def _parse_response(text: str, original_query: str) -> ClassifierOutput:
    """Extract the JSON block from the ADK response and validate it."""
    # Try ```json ... ``` fence first, then bare JSON.
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    raw = match.group(1).strip() if match else text.strip()

    try:
        data = json.loads(raw)
        return ClassifierOutput(
            task_type=data.get("task_type", "other"),
            policy_params=data.get("policy_params", {}),
            confidence=data.get("confidence", "medium"),
            cleaned_query=data.get("cleaned_query", original_query),
            reasoning=data.get("reasoning", ""),
        )
    except (json.JSONDecodeError, ValueError):
        return ClassifierOutput(
            task_type=PolicyTaskType.OTHER,
            policy_params={},
            confidence="low",
            cleaned_query=original_query,
            reasoning="ADK response could not be parsed as JSON.",
        )

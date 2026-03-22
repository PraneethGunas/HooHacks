"""
Premium Data Agent — fetches gated data via L402 Lightning payments.

Sits between Stage 1 (Analyst) and Stage 2 (Sector Agents) in the pipeline.
Evaluates what premium sources would strengthen the analysis, pays for them
via Lightning, and enriches the briefing packet.

Emits SSE events so the frontend can show Lightning payments in real time.

===========================================================================
INTEGRATION GUIDE
===========================================================================

STATUS: 🟢 REAL orchestration + 🟡 MOCKED scenario detection

WHAT'S REAL:
  - L402Client integration — actually pays Lightning invoices
  - Parallel fetching of all premium services
  - SSE event emission for real-time frontend updates
  - Payment metadata collection (hashes, amounts, durations)

WHAT'S MOCKED:
  - Scenario detection is keyword-based (SCENARIO_KEYWORDS dict below)
    Only recognizes 9 hardcoded keywords mapping to 3 demo scenarios.
    Any query that doesn't contain these keywords is silently skipped.
  - Service endpoints are hardcoded to 3 paths (PREMIUM_SERVICES dict)

TO MAKE THIS REAL:
  1. Replace detect_scenario() with an LLM call that classifies the
     user's query into a policy domain and extracts search parameters.
     [OWNER: Rudra — Agent/RAG module]

  2. Replace PREMIUM_SERVICES with a dynamic service registry, or have
     the Analyst Agent decide which premium sources to query.
     [OWNER: Rudra — Agent orchestration]

  3. The SSE events and L402Client are production-ready — no changes
     needed on the Lightning side.
     [OWNER: Praneeth — Lightning module]

  4. Frontend reads the SSE events emitted here to animate payments.
     [OWNER: Samank — Frontend module]
===========================================================================
"""

import asyncio
from typing import Any, Callable, Awaitable

from backend.config import settings
from backend.lightning.l402_client import L402Client, L402PaymentResult


# ---------------------------------------------------------------------------
# 🟡 MOCK: Hardcoded keyword → scenario mapping. Only 3 scenarios supported.
#
# TO MAKE REAL: Replace with LLM-based classification. Example:
#   async def detect_scenario(query: str) -> str | None:
#       response = await llm.classify(query, categories=["h1b", "student_loan", "tariff", ...])
#       return response.category
#
# OWNER: Rudra (Agent/RAG module)
# ---------------------------------------------------------------------------
SCENARIO_KEYWORDS = {
    "h1b": "h1b",
    "visa": "h1b",
    "immigration": "h1b",
    "student loan": "student_loan",
    "loan forgiveness": "student_loan",
    "student debt": "student_loan",
    "tariff": "tariff",
    "import": "tariff",
    "trade": "tariff",
}

# ---------------------------------------------------------------------------
# 🟡 MOCK: Hardcoded service endpoints — only 3 premium services exist.
#
# TO MAKE REAL: Build a service registry or let the Analyst Agent decide
# which sources to query dynamically based on the query domain.
#
# OWNER: Rudra (Agent orchestration) + Praneeth (new Aperture routes)
# ---------------------------------------------------------------------------
PREMIUM_SERVICES = {
    "legal": {"path": "/v1/legal/{scenario}", "name": "premium-legal-db"},
    "econ_models": {"path": "/v1/econ-models/{scenario}", "name": "premium-econ-models"},
    "research": {"path": "/v1/research/{scenario}", "name": "premium-research"},
}


def detect_scenario(query: str) -> str | None:
    """
    Match user query to a known demo scenario.

    🟡 MOCK: Simple keyword matching — only recognizes 3 demo scenarios.
    TO MAKE REAL: Replace with LLM classification or RAG-based routing.
    OWNER: Rudra
    """
    query_lower = query.lower()
    for keyword, scenario in SCENARIO_KEYWORDS.items():
        if keyword in query_lower:
            return scenario
    return None


class PremiumDataAgent:
    """
    Fetches premium data for a policy query via L402 payments.

    Usage:
        agent = PremiumDataAgent()
        results = await agent.run(
            query="How will the new H1B policy affect me?",
            on_event=my_sse_callback,
        )
    """

    def __init__(self, aperture_url: str = settings.aperture_url):
        self.aperture_url = aperture_url.rstrip("/")
        self.l402_client = L402Client(max_cost_sats=settings.lnget_max_cost_sats)

    async def run(
        self,
        query: str,
        on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """
        Run the premium data agent.

        Args:
            query: The user's policy question
            on_event: Optional async callback for SSE events (for real-time UI)

        Returns:
            Dict with premium data keyed by service type, plus payment metadata.
        """
        scenario = detect_scenario(query)
        if not scenario:
            # No matching demo scenario — skip premium data
            if on_event:
                await on_event({
                    "type": "agent_result",
                    "agent": "premium",
                    "data": {"status": "skipped", "reason": "No matching premium data sources"},
                })
            return {"premium_data": {}, "payments": []}

        # Notify frontend that premium agent is starting
        if on_event:
            await on_event({
                "type": "agent_start",
                "agent": "premium",
                "data": {"scenario": scenario, "services": list(PREMIUM_SERVICES.keys())},
            })

        # Fetch premium services sequentially — Lightning channel can't
        # reliably handle concurrent HTLC payments through the same channel.
        premium_data = {}
        payments = []

        for service_type, svc in PREMIUM_SERVICES.items():
            url = f"{self.aperture_url}{svc['path'].format(scenario=scenario)}"
            try:
                result = await self._fetch_with_events(
                    url=url,
                    service_name=svc["name"],
                    on_event=on_event,
                )
            except Exception:
                continue
            if result.success:
                premium_data[service_type] = result.data
                payments.append({
                    "service": result.service,
                    "amount_sats": result.invoice_amount_sats,
                    "payment_hash": result.payment_hash,
                    "duration_ms": result.duration_ms,
                })

        # Notify frontend of completion
        if on_event:
            await on_event({
                "type": "agent_result",
                "agent": "premium",
                "data": {
                    "status": "complete",
                    "services_accessed": list(premium_data.keys()),
                    "total_paid_sats": sum(p["amount_sats"] for p in payments),
                },
            })

        return {"premium_data": premium_data, "payments": payments}

    async def _fetch_with_events(
        self,
        url: str,
        service_name: str,
        on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> L402PaymentResult:
        """Fetch with SSE event emission for real-time UI."""
        # Emit "paying" event
        if on_event:
            await on_event({
                "type": "lightning_payment",
                "data": {
                    "service": service_name,
                    "status": "paying",
                    "invoice_amount_sats": 0,  # unknown until 402 received
                },
            })

        result = await self.l402_client.fetch(url, service_name=service_name)

        # Emit payment result event
        if on_event:
            await on_event({
                "type": "lightning_payment",
                "data": {
                    "service": service_name,
                    "status": "paid" if result.success else "failed",
                    "invoice_amount_sats": result.invoice_amount_sats,
                    "payment_hash": result.payment_hash,
                    "macaroon_received": bool(result.macaroon),
                    "duration_ms": result.duration_ms,
                    "error": result.error,
                },
            })

        return result

    async def close(self):
        await self.l402_client.close()

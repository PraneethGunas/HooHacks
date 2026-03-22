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

WHAT'S REAL (when lnget + Aperture + litd are running):
  - L402Client integration — actually pays Lightning invoices
  - Sequential fetching of all premium services
  - SSE event emission for real-time frontend updates
  - Payment metadata collection (hashes, amounts, durations)

GRACEFUL DEGRADATION (when lnget is NOT available):
  - Fetches premium data directly from the premium-data service (bypasses L402)
  - Emits identical lightning_payment SSE events with simulated payment metadata
  - Frontend shows the same Lightning UI either way
  - Logs clearly whether we're in real or demo mode

WHAT'S MOCKED:
  - Scenario detection is keyword-based (SCENARIO_KEYWORDS dict below)
  - Service endpoints are hardcoded to 3 paths (PREMIUM_SERVICES dict)

TO MAKE THIS REAL:
  1. Replace detect_scenario() with an LLM call.  [OWNER: Rudra]
  2. Replace PREMIUM_SERVICES with a dynamic registry.  [OWNER: Rudra]
  3. SSE events and L402Client are production-ready.  [OWNER: Praneeth]
  4. Frontend reads the SSE events emitted here.  [OWNER: Samank]
===========================================================================
"""

import asyncio
import hashlib
import json
import logging
import shutil
import time
from typing import Any, Callable, Awaitable

from backend.config import settings

logger = logging.getLogger(__name__)

# Check lnget availability once at import time
_LNGET_AVAILABLE = shutil.which("lnget") is not None

if _LNGET_AVAILABLE:
    from backend.lightning.l402_client import L402Client, L402PaymentResult


# ---------------------------------------------------------------------------
# Scenario detection (keyword-based fallback to "h1b")
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

PREMIUM_SERVICES = {
    "legal": {"path": "/v1/legal/{scenario}", "name": "premium-legal-db", "sats": 10},
    "econ_models": {"path": "/v1/econ-models/{scenario}", "name": "premium-econ-models", "sats": 25},
    "research": {"path": "/v1/research/{scenario}", "name": "premium-research", "sats": 15},
}

# Direct URL for premium-data service (bypasses Aperture/L402)
PREMIUM_DATA_DIRECT_URL = "http://localhost:8082"


def _get_inline_premium_data(scenario: str, service_type: str) -> dict[str, Any] | None:
    """Load premium data directly from the mock_services module (no HTTP needed)."""
    try:
        from backend.lightning.mock_services.premium_data import PREMIUM_DATA
        return PREMIUM_DATA.get(service_type, {}).get(scenario)
    except Exception as e:
        logger.warning(f"Could not import inline premium data: {e}")
        return None


def detect_scenario(query: str) -> str:
    """Match user query to a known demo scenario. Falls back to 'h1b'."""
    query_lower = query.lower()
    for keyword, scenario in SCENARIO_KEYWORDS.items():
        if keyword in query_lower:
            return scenario
    return "h1b"


class PremiumDataAgent:
    """
    Fetches premium data for a policy query via L402 payments.

    Two modes:
      1. REAL L402 — lnget available, Aperture running. Pays real invoices.
      2. DEMO MODE — lnget not available. Fetches data directly from
         premium-data service, emits simulated payment events for UI.
    """

    def __init__(self, aperture_url: str = settings.aperture_url):
        self.aperture_url = aperture_url.rstrip("/")
        self.use_real_l402 = _LNGET_AVAILABLE
        self.l402_client = None

        if self.use_real_l402:
            try:
                self.l402_client = L402Client(max_cost_sats=settings.lnget_max_cost_sats)
                logger.info("PremiumDataAgent: lnget found — using REAL L402 payments")
            except Exception as e:
                logger.warning(f"PremiumDataAgent: lnget init failed ({e}), falling back to demo mode")
                self.use_real_l402 = False
        else:
            logger.info("PremiumDataAgent: lnget not in PATH — using demo mode (direct fetch + simulated payments)")

    async def run(
        self,
        query: str,
        on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """Run the premium data agent (real L402 or demo mode)."""
        scenario = detect_scenario(query)
        logger.info(f"PremiumDataAgent: scenario={scenario}, mode={'real_l402' if self.use_real_l402 else 'demo'}")

        if on_event:
            await on_event({
                "type": "agent_start",
                "agent": "premium",
                "data": {
                    "scenario": scenario,
                    "services": list(PREMIUM_SERVICES.keys()),
                    "mode": "real_l402" if self.use_real_l402 else "demo",
                },
            })

        premium_data: dict[str, Any] = {}
        payments: list[dict[str, Any]] = []

        for service_type, svc in PREMIUM_SERVICES.items():
            if self.use_real_l402:
                result = await self._fetch_real_l402(scenario, service_type, svc, on_event)
            else:
                result = await self._fetch_demo(scenario, service_type, svc, on_event)

            if result:
                premium_data[service_type] = result["data"]
                payments.append(result["payment"])

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

    async def _fetch_real_l402(
        self,
        scenario: str,
        service_type: str,
        svc: dict,
        on_event: Callable | None,
    ) -> dict[str, Any] | None:
        """Fetch via real L402 (lnget + Aperture)."""
        url = f"{self.aperture_url}{svc['path'].format(scenario=scenario)}"
        service_name = svc["name"]

        if on_event:
            await on_event({
                "type": "lightning_payment",
                "data": {
                    "service": service_name,
                    "status": "paying",
                    "invoice_amount_sats": 0,
                },
            })

        try:
            result = await self.l402_client.fetch(url, service_name=service_name)
        except Exception as e:
            logger.error(f"L402 fetch failed for {service_name}: {e}")
            if on_event:
                await on_event({
                    "type": "lightning_payment",
                    "data": {
                        "service": service_name,
                        "status": "failed",
                        "invoice_amount_sats": 0,
                        "payment_hash": "",
                        "macaroon_received": False,
                        "duration_ms": 0,
                        "error": str(e),
                    },
                })
            return None

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

        if not result.success:
            return None

        return {
            "data": result.data,
            "payment": {
                "service": result.service,
                "amount_sats": result.invoice_amount_sats,
                "payment_hash": result.payment_hash,
                "duration_ms": result.duration_ms,
            },
        }

    async def _fetch_demo(
        self,
        scenario: str,
        service_type: str,
        svc: dict,
        on_event: Callable | None,
    ) -> dict[str, Any] | None:
        """
        Demo mode: fetch premium data directly (no L402), emit simulated
        payment events so the Lightning UI still renders.

        Tries HTTP to premium-data service first. If that's not running
        either (full local dev), falls back to importing mock data directly
        from the Python module.
        """
        service_name = svc["name"]
        sats = svc["sats"]

        # Emit "paying" event
        if on_event:
            await on_event({
                "type": "lightning_payment",
                "data": {
                    "service": service_name,
                    "status": "paying",
                    "invoice_amount_sats": sats,
                },
            })

        start = time.monotonic()
        data = None

        # Try 1: HTTP to premium-data service (if Docker is running it)
        try:
            import httpx
            path = svc["path"].format(scenario=scenario)
            url = f"{PREMIUM_DATA_DIRECT_URL}{path}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                logger.info(f"Demo mode: fetched {service_name} via HTTP ({url})")
        except Exception:
            pass

        # Try 2: Import mock data directly from the Python module
        if data is None:
            data = _get_inline_premium_data(scenario, service_type)
            if data:
                logger.info(f"Demo mode: loaded {service_name} from inline mock data")

        elapsed = (time.monotonic() - start) * 1000

        if data is None:
            logger.warning(f"Demo mode: no data available for {service_name}/{scenario}")
            if on_event:
                await on_event({
                    "type": "lightning_payment",
                    "data": {
                        "service": service_name,
                        "status": "failed",
                        "invoice_amount_sats": sats,
                        "payment_hash": "",
                        "macaroon_received": False,
                        "duration_ms": round(elapsed),
                        "error": "No premium data source available",
                    },
                })
            return None

        # Simulate a brief payment delay so the UI animation looks realistic
        await asyncio.sleep(0.3)

        fake_hash = hashlib.sha256(f"{service_name}:{scenario}:{time.time()}".encode()).hexdigest()[:64]

        if on_event:
            await on_event({
                "type": "lightning_payment",
                "data": {
                    "service": service_name,
                    "status": "paid",
                    "invoice_amount_sats": sats,
                    "payment_hash": fake_hash,
                    "macaroon_received": True,
                    "duration_ms": round(elapsed + 300),
                },
            })

        return {
            "data": data,
            "payment": {
                "service": service_name,
                "amount_sats": sats,
                "payment_hash": fake_hash,
                "duration_ms": round(elapsed + 300),
            },
        }

    async def close(self):
        if self.l402_client:
            await self.l402_client.close()

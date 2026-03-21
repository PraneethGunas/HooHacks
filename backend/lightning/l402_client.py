"""
L402 Client for PolicyPulse.

Uses `lnget` from Lightning Labs' lightning-agent-tools to handle
the entire L402 payment flow:
  - Detects 402 responses
  - Parses WWW-Authenticate header
  - Pays Lightning invoice (with spending limits)
  - Caches tokens per-domain (~/.lnget/tokens/)
  - Retries with valid auth

Install: go install github.com/lightninglabs/lnget/cmd/lnget@latest
Reference: https://github.com/lightninglabs/lightning-agent-tools

===========================================================================
INTEGRATION GUIDE
===========================================================================

STATUS: 🟢 FULLY REAL — No mocks. This is production-ready.

WHAT'S REAL:
  - Subprocess calls to real `lnget` binary (Lightning Labs)
  - Real L402 protocol handling (402 → pay → macaroon → retry)
  - Real Lightning invoice payments on regtest (real crypto, test network)
  - Token caching, timeout handling, error classification

WHAT'S HARDCODED (demo-safe defaults, not mocks):
  - max_cost_sats=500 — safety cap. Adjust via config.py / env vars.
  - insecure=True — allows self-signed TLS. Required for Docker regtest.
    Set to False for production with proper TLS.
  - timeout=30s — lnget subprocess timeout. Tune as needed.

FOR PRODUCTION:
  - Set insecure=False and use real TLS certs
  - Adjust max_cost_sats based on your budget per query
  - The lnget config at ~/.lnget/config.yaml controls LND connection.
    On mainnet, update network + macaroon path in bootstrap or manually.

OWNER: Praneeth (Lightning module)
===========================================================================
"""

import asyncio
import json
import shutil
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class L402PaymentResult:
    """Result of an L402 payment + data retrieval."""

    success: bool
    service: str
    data: dict[str, Any] | None = None
    invoice_amount_sats: int = 0
    payment_hash: str = ""
    payment_preimage: str = ""
    macaroon: str = ""
    duration_ms: float = 0
    error: str | None = None


class L402Client:
    """
    L402 HTTP client powered by lnget (lightning-agent-tools).

    lnget handles the entire L402 flow internally — 402 detection,
    invoice payment, token caching, spending limits, crash recovery.
    We wrap it as an async subprocess call and parse its output.

    Usage:
        client = L402Client()
        result = await client.fetch("http://aperture:8081/v1/legal/h1b")
        if result.success:
            print(result.data)
            print(f"Paid {result.invoice_amount_sats} sats")
    """

    def __init__(self, max_cost_sats: int = 500, insecure: bool = True):
        """
        Args:
            max_cost_sats: Max auto-pay amount per request (safety cap).
            insecure: Allow self-signed TLS (needed for local regtest Aperture).
        """
        if not shutil.which("lnget"):
            raise RuntimeError(
                "lnget not found in PATH. Install it:\n"
                "  go install github.com/lightninglabs/lnget/cmd/lnget@latest\n"
                "Or from lightning-agent-tools:\n"
                "  skills/lnget/scripts/install.sh"
            )
        self.max_cost_sats = max_cost_sats
        self.insecure = insecure

    async def fetch(self, url: str, service_name: str = "") -> L402PaymentResult:
        """
        Fetch data from an L402-gated endpoint.

        lnget handles payment, caching, and retry internally.
        """
        start = time.monotonic()
        service = service_name or url.split("/")[-2]

        cmd = [
            "lnget",
            "--json",
            "-q",
            f"--max-cost={self.max_cost_sats}",
        ]
        if self.insecure:
            cmd.append("-k")
        cmd.append(url)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=30.0
            )
        except asyncio.TimeoutError:
            return L402PaymentResult(
                success=False,
                service=service,
                error="lnget timed out after 30s",
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except FileNotFoundError:
            return L402PaymentResult(
                success=False,
                service=service,
                error="lnget binary not found in PATH",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        elapsed = (time.monotonic() - start) * 1000

        if proc.returncode != 0:
            error_msg = stderr.decode().strip() or f"lnget exit code {proc.returncode}"
            if proc.returncode == 2:
                error_msg = f"Invoice exceeds max cost ({self.max_cost_sats} sats): {error_msg}"
            return L402PaymentResult(
                success=False,
                service=service,
                error=error_msg,
                duration_ms=elapsed,
            )

        # Parse lnget output
        raw = stdout.decode().strip()
        try:
            output = json.loads(raw)
        except json.JSONDecodeError:
            return L402PaymentResult(
                success=False,
                service=service,
                error=f"Could not parse lnget output: {raw[:200]}",
                duration_ms=elapsed,
            )

        # lnget --json wraps the response; extract the body
        body = output.get("body", output)
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass

        return L402PaymentResult(
            success=True,
            service=service,
            data=body if isinstance(body, dict) else output,
            invoice_amount_sats=output.get("invoice_amount_sat", 0),
            payment_hash=output.get("payment_hash", ""),
            payment_preimage=output.get("payment_preimage", ""),
            macaroon=output.get("macaroon", ""),
            duration_ms=elapsed,
        )

    async def close(self):
        """No-op — lnget manages its own state. Kept for interface compatibility."""
        pass

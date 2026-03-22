#!/usr/bin/env python3
"""
End-to-end test for the L402 payment flow.

Prerequisites:
  - Docker Lightning stack running:
    docker compose -f docker/docker-compose.lightning.yml up --build
  - Bootstrap script completed (wallet funded, channel open)

Tests:
  1. Direct access to premium service (bypass Aperture) — should return data
  2. Access via Aperture without payment — should return 402
  3. Full L402 flow via L402Client — should pay and return data
  4. Cached token reuse — second request should skip payment

Usage:
  python scripts/test_l402_flow.py
  # Or with custom URLs:
  APERTURE_URL=http://localhost:8081 PREMIUM_URL=http://localhost:8082 python scripts/test_l402_flow.py
"""

import asyncio
import os
import sys
import json

import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.lightning.l402_client import L402Client, parse_l402_challenge


APERTURE_URL = os.environ.get("APERTURE_URL", "http://localhost:8081")
PREMIUM_URL = os.environ.get("PREMIUM_URL", "http://localhost:8082")

# Test scenarios
TEST_ENDPOINTS = [
    ("/v1/legal/h1b", "premium-legal-db"),
    ("/v1/econ-models/h1b", "premium-econ-models"),
    ("/v1/research/h1b", "premium-research"),
]


async def test_direct_access():
    """Test 1: Direct access to premium service (no L402 gate)."""
    print("\n=== Test 1: Direct access to premium service ===")
    async with httpx.AsyncClient() as client:
        for path, name in TEST_ENDPOINTS:
            url = f"{PREMIUM_URL}{path}"
            resp = await client.get(url)
            status = "PASS" if resp.status_code == 200 else "FAIL"
            print(f"  [{status}] {name}: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"         source: {data.get('source', 'N/A')}")


async def test_aperture_402():
    """Test 2: Aperture returns 402 without payment."""
    print("\n=== Test 2: Aperture returns 402 (no payment) ===")
    async with httpx.AsyncClient() as client:
        for path, name in TEST_ENDPOINTS:
            url = f"{APERTURE_URL}{path}"
            resp = await client.get(url)
            status = "PASS" if resp.status_code == 402 else "FAIL"
            print(f"  [{status}] {name}: {resp.status_code}")
            if resp.status_code == 402:
                www_auth = resp.headers.get("www-authenticate", "")
                try:
                    challenge = parse_l402_challenge(www_auth)
                    print(f"         macaroon: {challenge.macaroon[:40]}...")
                    print(f"         invoice:  {challenge.invoice[:40]}...")
                except ValueError as e:
                    print(f"         [WARN] Could not parse challenge: {e}")


async def test_full_l402_flow():
    """Test 3: Full L402 payment flow via L402Client."""
    print("\n=== Test 3: Full L402 payment flow ===")
    l402_client = L402Client()
    try:
        for path, name in TEST_ENDPOINTS:
            url = f"{APERTURE_URL}{path}"
            result = await l402_client.fetch(url, service_name=name)
            status = "PASS" if result.success else "FAIL"
            print(f"  [{status}] {name}")
            if result.success:
                print(f"         paid: {result.invoice_amount_sats} sats")
                print(f"         hash: {result.payment_hash[:20]}...")
                print(f"         time: {result.duration_ms:.0f}ms")
                print(f"         data source: {result.data.get('source', 'N/A')}")
            else:
                print(f"         error: {result.error}")
    finally:
        await l402_client.close()


async def test_token_cache():
    """Test 4: Second request reuses cached token (no second payment)."""
    print("\n=== Test 4: Token cache reuse ===")
    l402_client = L402Client()
    try:
        url = f"{APERTURE_URL}/v1/legal/h1b"

        # First request — should pay
        r1 = await l402_client.fetch(url, service_name="legal-first")
        if not r1.success:
            print(f"  [FAIL] First request failed: {r1.error}")
            return

        # Second request — should use cached token (no payment)
        r2 = await l402_client.fetch(url, service_name="legal-cached")
        status = "PASS" if r2.success and r2.invoice_amount_sats == 0 else "FAIL"
        print(f"  [{status}] Cache reuse")
        print(f"         first request:  paid {r1.invoice_amount_sats} sats in {r1.duration_ms:.0f}ms")
        print(f"         second request: paid {r2.invoice_amount_sats} sats in {r2.duration_ms:.0f}ms")
    finally:
        await l402_client.close()


async def test_premium_agent():
    """Test 5: Premium Data Agent integration."""
    print("\n=== Test 5: Premium Data Agent ===")
    from backend.lightning.premium_agent import PremiumDataAgent

    events = []

    async def capture_event(event):
        events.append(event)
        event_type = event.get("type", "unknown")
        data = event.get("data", {})
        if event_type == "lightning_payment":
            print(f"  [EVENT] {event_type}: {data.get('service')} — {data.get('status')}")
        else:
            print(f"  [EVENT] {event_type}: {data.get('status', json.dumps(data)[:60])}")

    agent = PremiumDataAgent(aperture_url=APERTURE_URL)
    try:
        result = await agent.run(
            query="How will the new H1B visa policy affect international students?",
            on_event=capture_event,
        )
        print(f"\n  Services accessed: {list(result['premium_data'].keys())}")
        print(f"  Total payments: {len(result['payments'])}")
        total_sats = sum(p['amount_sats'] for p in result['payments'])
        print(f"  Total paid: {total_sats} sats")
        status = "PASS" if len(result['premium_data']) > 0 else "FAIL"
        print(f"  [{status}] Agent completed")
    finally:
        await agent.close()


async def main():
    print("PolicyPulse L402 End-to-End Test Suite")
    print("=" * 50)

    await test_direct_access()
    await test_aperture_402()

    # Tests 3-5 require LND to be running and funded
    try:
        await test_full_l402_flow()
        await test_token_cache()
        await test_premium_agent()
    except Exception as e:
        print(f"\n  [SKIP] LND-dependent tests failed: {e}")
        print("  Make sure the Docker Lightning stack is running and bootstrapped.")

    print("\n" + "=" * 50)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())

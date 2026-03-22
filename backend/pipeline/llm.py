"""
LLM abstraction — routes calls to whichever provider has a key set.

Tries providers in order: Google (Gemini) → OpenAI → Anthropic.
Falls back to None if no keys are configured (stages handle this gracefully).

===========================================================================
INTEGRATION GUIDE
===========================================================================
OWNER: Rudra (swap with LangChain LLM wrapper if preferred)

Currently uses raw HTTP calls to avoid heavy SDK dependencies during hackathon.
Each provider's chat completion endpoint is called directly via httpx.
===========================================================================
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from backend.config import settings


async def llm_chat(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    fast: bool = False,
) -> str | None:
    """
    Send a chat completion request to the first available LLM provider.

    Args:
        system_prompt: System instruction
        user_prompt: User message
        json_mode: Request JSON output (best-effort)
        temperature: Sampling temperature
        max_tokens: Max response tokens
        fast: Use cheaper/faster model variant (for classifier)

    Returns:
        The assistant's response text, or None if no LLM keys are configured.
    """
    if settings.google_api_key:
        return await _gemini(system_prompt, user_prompt, json_mode, temperature, max_tokens, fast)
    if settings.openai_api_key:
        return await _openai(system_prompt, user_prompt, json_mode, temperature, max_tokens, fast)
    if settings.anthropic_api_key:
        return await _anthropic(system_prompt, user_prompt, json_mode, temperature, max_tokens, fast)
    return None


async def _gemini(
    system: str, user: str, json_mode: bool, temp: float, max_tokens: int, fast: bool
) -> str:
    model = "gemini-2.5-flash" if fast else "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": user}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "temperature": temp,
            "maxOutputTokens": max_tokens,
        },
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            params={"key": settings.google_api_key},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def _openai(
    system: str, user: str, json_mode: bool, temp: float, max_tokens: int, fast: bool
) -> str:
    model = "gpt-4o-mini" if fast else "gpt-4o"
    url = "https://api.openai.com/v1/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temp,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _anthropic(
    system: str, user: str, json_mode: bool, temp: float, max_tokens: int, fast: bool
) -> str:
    model = "claude-haiku-4-5-20251001" if fast else "claude-sonnet-4-5-20250514"
    url = "https://api.anthropic.com/v1/messages"

    if json_mode:
        system += "\n\nYou MUST respond with valid JSON only. No other text."

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temp,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


def parse_json_response(text: str) -> dict[str, Any]:
    """Extract JSON from an LLM response, handling markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        # Strip code fences
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)

from __future__ import annotations

import httpx

DEFAULT_TIMEOUT = 30.0
DEFAULT_HEADERS = {
    "User-Agent": "PolicyPulse/1.0 (HooHacks 2026; policypulse@hoohacks.io)",
}


class APIError(Exception):
    """Raised when an external API returns a non-success response."""

    def __init__(self, *, status_code: int, url: str, detail: str) -> None:
        self.status_code = status_code
        self.url = url
        self.detail = detail
        super().__init__(f"API error {status_code} from {url}: {detail[:200]}")


async def fetch_json(
    url: str,
    *,
    params: dict | None = None,
    method: str = "GET",
    json_body: dict | None = None,
    headers: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """Make an HTTP request and return parsed JSON.

    Raises APIError on non-200 responses.
    """
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.request(
            method, url, params=params, json=json_body, headers=merged_headers
        )
        if response.status_code != 200:
            raise APIError(
                status_code=response.status_code,
                url=url,
                detail=response.text[:500],
            )
        return response.json()


async def fetch_bytes(
    url: str,
    *,
    headers: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[bytes, str]:
    """Fetch raw bytes from a URL. Returns (content_bytes, content_type)."""
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers=merged_headers)
        if response.status_code != 200:
            raise APIError(
                status_code=response.status_code,
                url=url,
                detail=response.text[:500],
            )
        content_type = response.headers.get("content-type", "")
        return response.content, content_type

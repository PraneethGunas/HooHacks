from __future__ import annotations

import logging
import re
import tempfile

from bs4 import BeautifulSoup

from backend.tools._http import APIError, fetch_bytes, fetch_json
from backend.tools.schemas import FetchDocumentOutput

logger = logging.getLogger(__name__)

# Domains known to block automated requests
_BLOCKED_DOMAINS = [
    "onlinelibrary.wiley.com",
    "academic.oup.com",
    "www.sciencedirect.com",
    "link.springer.com",
    "www.jstor.org",
    "www.tandfonline.com",
]


def _extract_html(html_bytes: bytes) -> str:
    """Extract readable text from HTML, stripping boilerplate."""
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _extract_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF using pdfplumber."""
    import pdfplumber

    pages_text = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        with pdfplumber.open(tmp.name) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
    return "\n\n".join(pages_text)


def _extract_doi(url: str) -> str | None:
    """Extract DOI from a URL if present."""
    # doi.org/10.xxxx/yyyy or dx.doi.org/10.xxxx/yyyy
    match = re.search(r"(?:doi\.org/)(10\.\d{4,}/[^\s]+)", url)
    if match:
        return match.group(1)
    # Embedded DOI in publisher URL
    match = re.search(r"(10\.\d{4,}/[^\s?#]+)", url)
    if match:
        return match.group(1)
    return None


def _is_blocked_domain(url: str) -> bool:
    """Check if URL is from a known-blocked publisher."""
    return any(domain in url for domain in _BLOCKED_DOMAINS)


async def _try_unpaywall(doi: str) -> str | None:
    """Check Unpaywall for a free OA version of a paper. Returns URL or None."""
    try:
        data = await fetch_json(
            f"https://api.unpaywall.org/v2/{doi}",
            params={"email": "policypulse@hoohacks.io"},
            timeout=10,
        )
        if not data.get("is_oa"):
            return None
        # Prefer repository-hosted versions over publisher (less likely to block)
        for loc in data.get("oa_locations", []):
            if loc.get("host_type") == "repository":
                return loc.get("url_for_pdf") or loc.get("url")
        # Fall back to best OA location
        best = data.get("best_oa_location") or {}
        return best.get("url_for_pdf") or best.get("url")
    except Exception:
        return None


async def fetch_document_text(
    url: str, max_chars: int = 4000
) -> FetchDocumentOutput:
    """Fetch and extract readable text from a URL (HTML or PDF).

    For DOI URLs and known-blocked publisher domains, automatically checks
    Unpaywall for free open-access versions before attempting direct fetch.
    """
    original_url = url
    doi = _extract_doi(url)

    # If it's a DOI URL or blocked domain, try Unpaywall first
    if doi and (_is_blocked_domain(url) or "doi.org" in url):
        logger.info(f"DOI detected ({doi}), checking Unpaywall for OA version...")
        oa_url = await _try_unpaywall(doi)
        if oa_url and oa_url != url:
            logger.info(f"Unpaywall found OA URL: {oa_url}")
            url = oa_url

    # Attempt fetch
    try:
        raw_bytes, content_type = await fetch_bytes(url)
    except APIError as e:
        # If OA URL also failed and we have a DOI, try Unpaywall as fallback
        if doi and url == original_url:
            oa_url = await _try_unpaywall(doi)
            if oa_url and oa_url != url:
                try:
                    raw_bytes, content_type = await fetch_bytes(oa_url)
                except APIError:
                    pass
                else:
                    url = oa_url
                    # Successfully fetched OA version — continue below
                    if "pdf" in content_type.lower():
                        text = _extract_pdf(raw_bytes)
                        doc_type = "pdf"
                    else:
                        text = _extract_html(raw_bytes)
                        doc_type = "html"
                    truncated = len(text) > max_chars
                    if truncated:
                        text = text[:max_chars] + "\n[...truncated...]"
                    return FetchDocumentOutput(
                        url=url,
                        content=text if text else "[No readable content found]",
                        content_type=doc_type,
                        truncated=truncated,
                        char_count=len(text),
                    )

        return FetchDocumentOutput(
            url=original_url,
            content=f"[Failed to fetch: HTTP {e.status_code}. "
            f"This URL may be behind a paywall or Cloudflare protection. "
            f"Use abstracts from search_academic_papers instead of fetching full papers.]",
            content_type="error",
            truncated=False,
            char_count=0,
        )

    if "pdf" in content_type.lower():
        text = _extract_pdf(raw_bytes)
        doc_type = "pdf"
    else:
        text = _extract_html(raw_bytes)
        doc_type = "html"

    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + "\n[...truncated...]"

    return FetchDocumentOutput(
        url=url,
        content=text if text else "[No readable content found at this URL]",
        content_type=doc_type,
        truncated=truncated,
        char_count=len(text),
    )

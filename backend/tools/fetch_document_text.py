from __future__ import annotations

import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

from backend.tools._http import APIError, fetch_bytes
from backend.tools.schemas import FetchDocumentOutput


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


async def fetch_document_text(
    url: str, max_chars: int = 4000
) -> FetchDocumentOutput:
    """Fetch and extract readable text from a URL (HTML or PDF)."""
    try:
        raw_bytes, content_type = await fetch_bytes(url)
    except APIError as e:
        return FetchDocumentOutput(
            url=url,
            content=f"[Failed to fetch: HTTP {e.status_code} — {e.detail[:200]}]",
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

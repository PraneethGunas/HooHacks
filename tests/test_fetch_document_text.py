import pytest
from backend.tools.fetch_document_text import fetch_document_text
from backend.tools.schemas import FetchDocumentOutput


@pytest.mark.asyncio
async def test_fetch_html():
    """Fetch a Wikipedia page (reliable, no Cloudflare)."""
    result = await fetch_document_text(
        url="https://en.wikipedia.org/wiki/Minimum_wage", max_chars=2000
    )
    assert isinstance(result, FetchDocumentOutput)
    assert result.content_type == "html"
    assert len(result.content) > 100
    assert result.char_count > 0
    print(f"\nHTML fetch: {result.char_count} chars, truncated={result.truncated}")
    print(f"  First 200 chars: {result.content[:200]}")


@pytest.mark.asyncio
async def test_fetch_truncation():
    """Verify truncation works correctly."""
    result = await fetch_document_text(
        url="https://en.wikipedia.org/wiki/Minimum_wage", max_chars=500
    )
    assert isinstance(result, FetchDocumentOutput)
    assert result.truncated is True
    assert "[...truncated...]" in result.content
    print(f"\nTruncation test: {result.char_count} chars, truncated={result.truncated}")


@pytest.mark.asyncio
async def test_fetch_blocked_site():
    """Verify graceful handling when a site blocks access (Cloudflare etc)."""
    result = await fetch_document_text(
        url="https://www.cbo.gov/publication/55410", max_chars=2000
    )
    assert isinstance(result, FetchDocumentOutput)
    # Should return either content or a graceful error — not crash
    print(f"\nCBO fetch: type={result.content_type}, chars={result.char_count}")
    print(f"  Content preview: {result.content[:150]}")

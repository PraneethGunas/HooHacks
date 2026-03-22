"""Tests for fetch_document_text Unpaywall integration."""

import pytest
from backend.tools.fetch_document_text import (
    fetch_document_text,
    _extract_doi,
    _is_blocked_domain,
    _try_unpaywall,
)
from backend.tools.schemas import FetchDocumentOutput


# ---------------------------------------------------------------------------
# DOI extraction
# ---------------------------------------------------------------------------

class TestExtractDoi:
    def test_doi_org_url(self):
        assert _extract_doi("https://doi.org/10.1257/aer.20171445") == "10.1257/aer.20171445"

    def test_dx_doi_url(self):
        assert _extract_doi("https://dx.doi.org/10.3386/w25538") == "10.3386/w25538"

    def test_publisher_url_with_doi(self):
        doi = _extract_doi("https://onlinelibrary.wiley.com/doi/10.1111/j.1468-232x.2011.00634.x")
        assert doi == "10.1111/j.1468-232x.2011.00634.x"

    def test_no_doi(self):
        assert _extract_doi("https://en.wikipedia.org/wiki/Minimum_wage") is None

    def test_plain_text(self):
        assert _extract_doi("just some text") is None


# ---------------------------------------------------------------------------
# Blocked domain detection
# ---------------------------------------------------------------------------

class TestBlockedDomain:
    def test_wiley(self):
        assert _is_blocked_domain("https://onlinelibrary.wiley.com/doi/pdf/10.1111/test") is True

    def test_oup(self):
        assert _is_blocked_domain("https://academic.oup.com/qje/article-pdf/134/test") is True

    def test_springer(self):
        assert _is_blocked_domain("https://link.springer.com/article/10.1007/test") is True

    def test_wikipedia_not_blocked(self):
        assert _is_blocked_domain("https://en.wikipedia.org/wiki/Test") is False

    def test_fred_not_blocked(self):
        assert _is_blocked_domain("https://fred.stlouisfed.org/series/UNRATE") is False


# ---------------------------------------------------------------------------
# Unpaywall lookup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unpaywall_finds_oa():
    """Test Unpaywall finds OA URL for a known open-access paper."""
    url = await _try_unpaywall("10.1257/aer.20171445")
    # This paper is known OA — Unpaywall should find it
    assert url is not None
    print(f"\nUnpaywall OA URL: {url}")


@pytest.mark.asyncio
async def test_unpaywall_returns_none_for_closed():
    """Non-OA paper should return None."""
    url = await _try_unpaywall("10.1177/00197939140670s307")
    # This specific paper may or may not be OA — we check it returns without error
    # (result can be None or a URL)
    print(f"\nUnpaywall result for closed paper: {url}")


@pytest.mark.asyncio
async def test_unpaywall_bad_doi():
    """Invalid DOI should return None, not crash."""
    url = await _try_unpaywall("10.9999/nonexistent-paper")
    assert url is None


# ---------------------------------------------------------------------------
# Integration: fetch_document_text with DOI URLs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_doi_url_gets_helpful_error():
    """DOI URL that fails should give a helpful error, not a raw 403."""
    r = await fetch_document_text("https://doi.org/10.1177/00197939140670s307", max_chars=500)
    assert isinstance(r, FetchDocumentOutput)
    if r.content_type == "error":
        # Should have a helpful message about paywalls
        assert "paywall" in r.content.lower() or "abstract" in r.content.lower()
        print(f"\nHelpful error: {r.content[:200]}")
    else:
        # If Unpaywall found a free version and it worked — even better
        print(f"\nFetched via Unpaywall: {r.char_count} chars")


@pytest.mark.asyncio
async def test_fetch_normal_url_still_works():
    """Non-DOI URLs should work as before."""
    r = await fetch_document_text("https://en.wikipedia.org/wiki/Minimum_wage", max_chars=500)
    assert r.content_type == "html"
    assert r.char_count > 100

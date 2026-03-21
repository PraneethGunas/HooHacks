from __future__ import annotations

import logging

from backend.config import settings
from backend.tools._http import fetch_json
from backend.tools.schemas import AcademicPaper, SearchPapersOutput

logger = logging.getLogger(__name__)

S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

FIELDS = "title,year,citationCount,tldr,abstract,authors,externalIds,publicationTypes,url"


async def search_academic_papers(
    query: str, year_range: str = "2015-2026", limit: int = 5
) -> SearchPapersOutput:
    """Search Semantic Scholar for academic papers on economic topics."""
    params: dict = {
        "query": query,
        "limit": limit,
        "fields": FIELDS,
    }

    # Parse year range
    parts = year_range.split("-")
    if len(parts) == 2:
        params["year"] = f"{parts[0]}-{parts[1]}"

    headers: dict = {}
    if settings.semantic_scholar_key:
        headers["x-api-key"] = settings.semantic_scholar_key
    else:
        logger.warning(
            "SEMANTIC_SCHOLAR_KEY not set. Using unauthenticated access (100 req/5min)."
        )

    data = await fetch_json(S2_SEARCH_URL, params=params, headers=headers or None)

    papers = []
    for p in data.get("data", []):
        tldr_text = None
        if p.get("tldr"):
            tldr_text = p["tldr"].get("text")

        abstract = p.get("abstract")
        if abstract and len(abstract) > 500:
            abstract = abstract[:500]

        authors = [a["name"] for a in (p.get("authors") or [])[:3]]

        pub_types = p.get("publicationTypes") or []
        paper_type = pub_types[0] if pub_types else None

        url = p.get("url", "")

        papers.append(
            AcademicPaper(
                title=p.get("title", ""),
                year=p.get("year"),
                citations=p.get("citationCount", 0),
                tldr=tldr_text,
                abstract=abstract,
                authors=authors,
                url=url,
                type=paper_type,
            )
        )

    return SearchPapersOutput(
        results=papers,
        query=query,
        total_results=data.get("total", len(papers)),
    )

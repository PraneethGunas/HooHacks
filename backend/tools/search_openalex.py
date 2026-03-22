from __future__ import annotations

from backend.config import settings
from backend.tools._http import fetch_json
from backend.tools.schemas import OpenAlexWork, SearchOpenAlexOutput

OPENALEX_URL = "https://api.openalex.org/works"


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct readable text from an OpenAlex inverted index abstract."""
    if not inverted_index:
        return None
    max_pos = max(pos for positions in inverted_index.values() for pos in positions)
    words = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    text = " ".join(words)
    return text[:500] if len(text) > 500 else text


async def search_openalex(
    query: str, sort_by: str = "relevance_score", limit: int = 5
) -> SearchOpenAlexOutput:
    """Search OpenAlex for academic works on economic topics.

    IMPORTANT: Use quoted phrases for multi-word policy concepts to get
    relevant results. E.g., '"minimum wage" employment' not 'minimum wage employment'.
    """
    params = {
        "search": query,
        "per_page": limit,
        "mailto": settings.openalex_email,
        "sort": f"{sort_by}:desc",
        "filter": "type:article",  # Exclude books, reports, datasets — reduces noise
    }
    data = await fetch_json(OPENALEX_URL, params=params)

    works = []
    for w in data.get("results", []):
        abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))

        authors = [
            a["author"]["display_name"]
            for a in (w.get("authorships") or [])[:3]
            if a.get("author", {}).get("display_name")
        ]

        oa = w.get("open_access") or {}

        works.append(
            OpenAlexWork(
                title=w.get("title", ""),
                year=w.get("publication_year"),
                citations=w.get("cited_by_count", 0),
                abstract=abstract,
                doi=w.get("doi"),
                open_access_url=oa.get("oa_url"),
                authors=authors,
            )
        )

    return SearchOpenAlexOutput(results=works, query=query)

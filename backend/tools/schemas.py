from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# FRED Search
# ---------------------------------------------------------------------------

class FredSeriesMatch(BaseModel):
    id: str
    title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    last_updated: str
    popularity: int


class FredSearchOutput(BaseModel):
    results: list[FredSeriesMatch]
    query: str
    total_results: int


# ---------------------------------------------------------------------------
# FRED Get Series
# ---------------------------------------------------------------------------

class FredObservation(BaseModel):
    date: str
    value: str | None


class FredSeriesOutput(BaseModel):
    series_id: str
    title: str
    units: str
    frequency: str
    latest_value: str | None
    latest_date: str | None
    recent_observations: list[FredObservation]
    total_observations: int


# ---------------------------------------------------------------------------
# BLS Get Data
# ---------------------------------------------------------------------------

class BlsObservation(BaseModel):
    year: str
    period: str
    value: str
    pct_change: str | None = None


class BlsSeriesData(BaseModel):
    series_id: str
    data: list[BlsObservation]


class BlsGetDataOutput(BaseModel):
    results: list[BlsSeriesData]


# ---------------------------------------------------------------------------
# Search Academic Papers (Semantic Scholar)
# ---------------------------------------------------------------------------

class AcademicPaper(BaseModel):
    title: str
    year: int | None = None
    citations: int = 0
    tldr: str | None = None
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    url: str
    type: str | None = None


class SearchPapersOutput(BaseModel):
    results: list[AcademicPaper]
    query: str
    total_results: int


# ---------------------------------------------------------------------------
# Search OpenAlex
# ---------------------------------------------------------------------------

class OpenAlexWork(BaseModel):
    title: str
    year: int | None = None
    citations: int = 0
    abstract: str | None = None
    doi: str | None = None
    open_access_url: str | None = None
    authors: list[str] = Field(default_factory=list)


class SearchOpenAlexOutput(BaseModel):
    results: list[OpenAlexWork]
    query: str


# ---------------------------------------------------------------------------
# Search CBO Reports
# ---------------------------------------------------------------------------

class CBOReport(BaseModel):
    title: str
    url: str
    snippet: str
    score: float


class SearchCBOOutput(BaseModel):
    results: list[CBOReport]
    query: str


# ---------------------------------------------------------------------------
# Web Search News
# ---------------------------------------------------------------------------

class NewsArticle(BaseModel):
    title: str
    url: str
    content: str
    published_date: str | None = None


class WebSearchOutput(BaseModel):
    results: list[NewsArticle]
    query: str


# ---------------------------------------------------------------------------
# Fetch Document Text
# ---------------------------------------------------------------------------

class FetchDocumentOutput(BaseModel):
    url: str
    content: str
    content_type: str
    truncated: bool
    char_count: int


# ---------------------------------------------------------------------------
# Census ACS Query
# ---------------------------------------------------------------------------

class CensusACSOutput(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    geography: str = ""
    year: int = 0
    variables_requested: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# BEA Regional Data
# ---------------------------------------------------------------------------

class BEADataPoint(BaseModel):
    year: str = ""
    value: str = ""
    geo_name: str = ""
    unit: str = ""


class BEARegionalOutput(BaseModel):
    table_name: str = ""
    geo_fips: str = ""
    data: list[BEADataPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# HUD Data
# ---------------------------------------------------------------------------

class HUDDataOutput(BaseModel):
    dataset: str = ""
    entity_id: str = ""
    data: dict | list = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Code Execute
# ---------------------------------------------------------------------------

class CodeExecuteOutput(BaseModel):
    stdout: str = ""
    result: str | None = None
    error: str | None = None
    execution_time_ms: float = 0

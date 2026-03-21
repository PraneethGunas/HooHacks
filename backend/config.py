"""
PolicyPulse backend configuration — loaded from environment variables.

===========================================================================
INTEGRATION GUIDE
===========================================================================

STATUS: 🟡 DEFAULTS ONLY — All API keys are empty strings.

All settings can be overridden via environment variables or a .env file
in the project root. Pydantic auto-maps env vars to field names
(case-insensitive). Example .env:

    OPENAI_API_KEY=sk-...
    GOOGLE_API_KEY=AIza...
    APERTURE_URL=http://aperture:8081

OWNER: Everyone — each team member sets keys for their module.
===========================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

# Resolve .env relative to project root (two levels up from this file)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = {"env_file": str(_ENV_PATH), "env_file_encoding": "utf-8"}

    # --- LLM ---
    # 🔴 REQUIRED: At least one LLM key needed for agent pipeline.
    # OWNER: Rudra — set whichever LLM(s) you're using for agents.
    openai_api_key: str = ""       # For GPT-4 agent calls
    google_api_key: str = ""       # For Gemini agent calls
    anthropic_api_key: str = ""    # For Claude agent calls

    # --- Data APIs ---
    # OWNER: Rudra (tools pipeline) — keys for real data sources.
    fred_api_key: str = Field("", description="FRED API key")
    bls_api_key: Optional[str] = Field(None, description="BLS API key (optional)")
    bea_api_key: str = ""          # Bureau of Economic Analysis
    tavily_api_key: str = Field("", description="Tavily API key")
    semantic_scholar_key: Optional[str] = Field(None, description="Semantic Scholar API key (optional)")
    openalex_email: str = Field("policypulse@hoohacks.io", description="Email for OpenAlex polite pool")
    census_api_key: str = ""       # Census Bureau

    # --- Lightning ---
    # 🟢 REAL: L402 payments handled entirely by lnget (lightning-agent-tools).
    # OWNER: Praneeth — these defaults work for Docker regtest.
    aperture_url: str = "http://localhost:8081"  # Aperture L402 proxy
    lnget_max_cost_sats: int = 500               # Max auto-pay per request (sats)

    # --- App ---
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM routing
    llm_provider: str = Field("gemini", description="LLM provider: gemini, openai, or anthropic")
    llm_model_name: str = Field("gemini-2.5-flash", description="LLM model name")


settings = Settings()

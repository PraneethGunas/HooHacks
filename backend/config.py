from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

# Resolve .env relative to project root (two levels up from this file)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = {"env_file": str(_ENV_PATH), "env_file_encoding": "utf-8"}

    fred_api_key: str = Field(..., description="FRED API key")
    bls_api_key: Optional[str] = Field(None, description="BLS API key (optional)")
    tavily_api_key: str = Field(..., description="Tavily API key")
    semantic_scholar_key: Optional[str] = Field(None, description="Semantic Scholar API key (optional)")
    openalex_email: str = Field("policypulse@hoohacks.io", description="Email for OpenAlex polite pool")

    # LLM settings
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    llm_provider: str = Field("gemini", description="LLM provider: gemini, openai, or anthropic")
    llm_model_name: str = Field("gemini-2.5-flash", description="LLM model name")


settings = Settings()

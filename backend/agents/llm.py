from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from backend.config import settings


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """Return the configured chat model. Provider set via LLM_PROVIDER env var."""
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model_name,
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model_name,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model_name,
            api_key=settings.anthropic_api_key,
            temperature=0.2,
        )
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {provider}. Use 'gemini', 'openai', or 'anthropic'."
        )

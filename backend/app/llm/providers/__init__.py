from __future__ import annotations

from app.core.settings import settings
from app.llm.providers.base import LLMProvider
from app.llm.providers.lm_studio import LmStudioProvider
from app.llm.providers.ollama import OllamaProvider


def get_provider() -> LLMProvider:
    provider_name = (settings.LLM_PROVIDER or "ollama").lower()
    if provider_name == "ollama":
        return OllamaProvider()
    if provider_name in {"lmstudio", "lm-studio", "lm_studio"}:
        return LmStudioProvider()
    raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

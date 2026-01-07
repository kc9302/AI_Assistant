from __future__ import annotations

import logging
from typing import Any

import requests
from langchain_community.chat_models import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings

from app.core.settings import settings
from app.llm.providers.base import LLMProvider, ProviderHealth

logger = logging.getLogger(__name__)


class LmStudioProvider(LLMProvider):
    name = "lmstudio"

    def __init__(self) -> None:
        self._base_url = settings.LLM_BASE_URL
        self._api_key = settings.LLM_API_KEY or "lm-studio"

    def _filter_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        # Remove Ollama-specific fields to avoid ChatOpenAI validation errors.
        return {
            key: value
            for key, value in kwargs.items()
            if key not in {"format", "ollama_kwargs"}
        }

    def get_chat_model(
        self,
        *,
        model: str,
        keep_alive: str | None = None,
        **kwargs: Any,
    ) -> ChatOpenAI:
        _ = keep_alive
        clean_kwargs = self._filter_kwargs(kwargs)
        return ChatOpenAI(
            model=model,
            temperature=0.0,
            api_key=self._api_key,
            base_url=self._base_url,
            **clean_kwargs,
        )

    def get_embeddings(self, *, model: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            model=model,
            api_key=self._api_key,
            base_url=self._base_url,
        )

    def ensure_embedding_model(self, model: str) -> None:
        _ = model

    def prime(self, *, model: str, keep_alive: str | None = None) -> None:
        _ = keep_alive
        llm = self.get_chat_model(model=model)
        llm.invoke("Hello")

    def unload(self, *, model: str | None = None) -> None:
        _ = model

    def health(self) -> ProviderHealth:
        try:
            response = requests.get(f"{self._base_url}/models", timeout=2)
            ok = response.status_code == 200
            return ProviderHealth(ok=ok, base_url=self._base_url)
        except Exception as exc:
            return ProviderHealth(ok=False, base_url=self._base_url, details=str(exc))

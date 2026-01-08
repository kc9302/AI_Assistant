from __future__ import annotations

import logging
from typing import Any

import ollama
import requests
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.settings import settings
from app.llm.providers.base import LLMProvider, ProviderHealth

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        self._base_url = settings.LLM_BASE_URL

    def get_chat_model(
        self,
        *,
        model: str,
        keep_alive: str | None = None,
        **kwargs: Any,
    ) -> ChatOllama:
        ollama_kwargs: dict[str, Any] = {}
        if keep_alive is not None:
            ollama_kwargs["keep_alive"] = keep_alive
        elif settings.LLM_KEEP_ALIVE:
            ollama_kwargs["keep_alive"] = settings.LLM_KEEP_ALIVE

        model_format = kwargs.pop("format", "json")
        if model_format is None:
            model_format = ""

        return ChatOllama(
            base_url=self._base_url,
            model=model,
            temperature=0.0,
            format=model_format,
            ollama_kwargs=ollama_kwargs,
            **kwargs,
        )

    def get_embeddings(self, *, model: str) -> OllamaEmbeddings:
        return OllamaEmbeddings(
            base_url=self._base_url,
            model=model,
        )

    def ensure_embedding_model(self, model: str) -> None:
        client = ollama.Client(host=self._base_url)
        try:
            client.pull(model)
        except Exception as exc:
            logger.warning("Ollama embedding pull failed: %s", exc)

    def prime(self, *, model: str, keep_alive: str | None = None) -> None:
        llm = self.get_chat_model(model=model, keep_alive=keep_alive)
        llm.invoke("Hello")

    def unload(self, *, model: str | None = None) -> None:
        model_name = model or settings.LLM_MODEL
        client = ollama.Client(host=self._base_url)
        client.generate(model=model_name, prompt="Hi", keep_alive=0)

    def health(self) -> ProviderHealth:
        try:
            response = requests.get(self._base_url, timeout=2)
            ok = response.status_code == 200
            return ProviderHealth(ok=ok, base_url=self._base_url)
        except Exception as exc:
            return ProviderHealth(ok=False, base_url=self._base_url, details=str(exc))

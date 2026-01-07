from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel


@dataclass(frozen=True)
class ProviderHealth:
    ok: bool
    base_url: str | None = None
    details: str | None = None


class LLMProvider(Protocol):
    name: str

    def get_chat_model(
        self,
        *,
        model: str,
        keep_alive: str | None = None,
        **kwargs: Any,
    ) -> BaseChatModel: ...

    def get_embeddings(self, *, model: str) -> Embeddings: ...

    def ensure_embedding_model(self, model: str) -> None: ...

    def prime(self, *, model: str, keep_alive: str | None = None) -> None: ...

    def unload(self, *, model: str | None = None) -> None: ...

    def health(self) -> ProviderHealth: ...

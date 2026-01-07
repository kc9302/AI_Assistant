from app.core.settings import settings
from app.llm.providers import get_provider
import logging

logger = logging.getLogger(__name__)

def get_llm(keep_alive: str = "0", **kwargs):
    """Returns a configured chat model for the active provider."""
    provider = get_provider()
    model_name = kwargs.pop("model", settings.LLM_MODEL)
    llm = provider.get_chat_model(model=model_name, keep_alive=keep_alive, **kwargs)
    logger.info("Initialized %s chat model [%s] - keep_alive=%s", provider.name, model_name, keep_alive)
    return llm


def get_embeddings(model: str | None = None):
    """Returns a configured embeddings client for the active provider."""
    provider = get_provider()
    embedding_model = model or settings.LLM_EMBEDDING_MODEL
    embeddings = provider.get_embeddings(model=embedding_model)
    logger.info("Initialized %s embeddings model [%s]", provider.name, embedding_model)
    return embeddings


def ensure_embedding_model(model: str | None = None) -> None:
    """Ensures the embeddings model is available for the active provider."""
    provider = get_provider()
    embedding_model = model or settings.LLM_EMBEDDING_MODEL
    provider.ensure_embedding_model(embedding_model)


def init_models():
    """Primes the remote model by making a small request to ensure it is loaded."""
    logger.info("Priming models for startup...")
    try:
        provider = get_provider()
        provider.prime(model=settings.LLM_MODEL, keep_alive="5m")
        logger.info("Remote model primed.")
    except Exception as e:
        logger.warn(f"Model priming failed (this is non-critical): {e}")


def unload_model() -> None:
    """Request the provider to unload the current model, if supported."""
    provider = get_provider()
    provider.unload(model=settings.LLM_MODEL)


def provider_health():
    """Return provider health details for status endpoint."""
    provider = get_provider()
    return provider.health()


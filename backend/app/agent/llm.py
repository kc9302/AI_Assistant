from app.core.settings import settings
from app.llm.providers import get_provider
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# LLM Instance Cache: (model_name, is_complex, format) -> model_instance
_llm_cache: Dict[tuple, Any] = {}

def get_llm(keep_alive: str | None = None, **kwargs):
    """
    Returns a configured chat model for the active provider.
    Enhanced with complexity-aware GPU scheduling and instance caching.
    """
    provider = get_provider()
    model_name = kwargs.pop("model", settings.LLM_MODEL)
    is_complex = kwargs.pop("is_complex", False)
    model_format = kwargs.pop("format", "json")
    
    # Use provided keep_alive or fallback to settings
    effective_keep_alive = keep_alive or settings.LLM_KEEP_ALIVE

    # Simple cache key
    cache_key = (model_name, is_complex, model_format)
    
    if cache_key in _llm_cache:
        logger.debug("Using cached LLM instance for %s", cache_key)
        return _llm_cache[cache_key]

    # Logic for dual GPU usage/high performance
    if is_complex and provider.name == "ollama":
        # Multi-GPU Optimization: 
        # 1. num_gpu=-1 lets Ollama decide layer distribution automatically across available GPUs (0,1).
        # 2. num_ctx=8192 for complex reasoning tasks.
        kwargs["num_gpu"] = -1 
        kwargs["num_ctx"] = 8192
        logger.info("[GPU_LOAD_BALANCE] Complex query: Balanced GPU distribution (-1) & 8k Context enabled.")

    llm = provider.get_chat_model(model=model_name, keep_alive=effective_keep_alive, **kwargs)
    
    # Add retry logic for transient errors (Network, GPU busy, etc.)
    llm = llm.with_retry(stop_after_attempt=2)
    
    # Cache the instance
    _llm_cache[cache_key] = llm
    
    logger.info("Initialized and cached %s chat model [%s] with retry - keep_alive=%s (Complex=%s)", 
                provider.name, model_name, effective_keep_alive, is_complex)
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
        # Use get_llm to ensure it's cached and loaded with proper keep_alive
        llm = get_llm(keep_alive="10m") 
        provider = get_provider()
        provider.prime(model=settings.LLM_MODEL, keep_alive="10m")
        logger.info("Remote model primed.")
    except Exception as e:
        logger.warn(f"Model priming failed (this is non-critical): {e}")


def unload_model() -> None:
    """Request the provider to unload the current model, if supported."""
    # Clear cache when unloading
    _llm_cache.clear()
    provider = get_provider()
    provider.unload(model=settings.LLM_MODEL)
    logger.info("LLM cache cleared and model unload requested.")


def provider_health():
    """Return provider health details for status endpoint."""
    provider = get_provider()
    return provider.health()

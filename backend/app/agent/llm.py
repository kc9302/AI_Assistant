from langchain_ollama import ChatOllama
from langchain_community.llms import LlamaCpp
from app.core.settings import settings
import logging
import os

logger = logging.getLogger(__name__)

def get_llm(keep_alive: str = "0", **kwargs):
    """Returns a configured ChatOllama instance for remote models."""
    ollama_kwargs = {}
    if keep_alive is not None:
        ollama_kwargs["keep_alive"] = keep_alive
    elif settings.OLLAMA_KEEP_ALIVE:
        ollama_kwargs["keep_alive"] = settings.OLLAMA_KEEP_ALIVE

    # Use model from kwargs or default from settings
    model_name = kwargs.pop("model", settings.OLLAMA_MODEL)

    import time
    start_time = time.time()
    
    llm = ChatOllama(
        base_url=settings.OLLAMA_HOST,
        model=model_name,
        temperature=0.0,
        format="json", # Force JSON output
        ollama_kwargs=ollama_kwargs, # Pass ollama_kwargs
        **kwargs
    )
    
    # We log initialization. Invoke timing will be handled in the nodes for better context.
    logger.info(f"Initialized ChatOllama [{model_name}] - keep_alive={keep_alive}")
    return llm


def init_models():
    """Primes the remote model by making a small request to ensure it is loaded."""
    logger.info("Priming models for startup...")
    try:
        # Prime remote model (Ollama)
        remote_llm = get_llm(keep_alive="5m") # Keep remote model for 5m after first load
        remote_llm.invoke("Hello")
        logger.info("Remote model primed.")
    except Exception as e:
        logger.warn(f"Model priming failed (this is non-critical): {e}")


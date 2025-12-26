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



def get_local_llm():
    """Returns a LlamaCpp instance for the local executor model."""
    model_path = os.path.abspath(settings.OLLAMA_MODEL_EXECUTOR_PATH)
    if not os.path.exists(model_path):
        logger.error(f"Local model not found at {model_path}")
        return None
        
    logger.info(f"Initializing Local LlamaCpp with model={model_path}")
    try:
        # We use settings optimized for FunctionGemma-270M
        llm = LlamaCpp(
            model_path=model_path,
            temperature=0.0,
            max_tokens=1024, # Increased for complex plans
            n_ctx=4096, # Increased from 2048 to support 32k capabilities (within limits)
            verbose=False,
            stop=["<|end|>", "<|im_end|>", "<|user|>", "<|system|>", "<|assistant|>", "\n\n\n"],
            streaming=False,
            repeat_penalty=1.1,
            f16_kv=True, # Better performance on modern CPUs/GPUs
        )
        return llm

    except Exception as e:
        logger.error(f"Failed to initialize local LLM: {e}")
        return None

def init_models():
    """Primes the models by making a small request to ensure they are loaded."""
    logger.info("Priming models for startup...")
    try:
        # Prime local model
        local_llm = get_local_llm()
        if local_llm:
            local_llm.invoke("Hi")
            logger.info("Local model primed.")
        
        # Prime remote model (Ollama)
        remote_llm = get_llm(keep_alive="5m") # Keep remote model for 5m after first load
        remote_llm.invoke("Hello")
        logger.info("Remote model primed.")
    except Exception as e:
        logger.warn(f"Model priming failed (this is non-critical): {e}")


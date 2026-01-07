import os
import sys
import logging

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.travel import travel_knowledge_service
from app.agent.llm import ensure_embedding_model
from app.core.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def index_travel_data():
    """
    Script to index travel documents into FAISS vector DB.
    """
    # 1. Ensure embedding model is available for the active provider
    logger.info(
        "Ensuring embedding model '%s' is available at %s...",
        settings.LLM_EMBEDDING_MODEL,
        settings.LLM_BASE_URL,
    )
    try:
        ensure_embedding_model(settings.LLM_EMBEDDING_MODEL)
        logger.info("Embedding model ready.")
    except Exception as pull_err:
        logger.warning("Failed to ensure embedding model: %s", pull_err)
    
    # 2. Build index
    try:
        travel_knowledge_service.build_index()
        logger.info("Travel data indexing complete.")
    except Exception as e:
        logger.error(f"Indexing failed: {e}")

if __name__ == "__main__":
    index_travel_data()

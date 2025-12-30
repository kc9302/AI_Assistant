import os
import sys
import logging

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.travel import travel_knowledge_service
from app.agent.llm import get_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def index_travel_data():
    """
    Script to index travel documents into FAISS vector DB.
    """
    # 1. Ensure embedding model is pulled (Ollama)
    import ollama
    from app.core.settings import settings
    client = ollama.Client(host=settings.OLLAMA_HOST)
    logger.info(f"Ensuring embedding model 'nomic-embed-text' is available at {settings.OLLAMA_HOST}...")
    try:
        client.pull("nomic-embed-text")
        logger.info("Embedding model ready.")
    except Exception as pull_err:
        logger.warning(f"Failed to pull model via library: {pull_err}")
    
    # 2. Build index
    try:
        travel_knowledge_service.build_index()
        logger.info("Travel data indexing complete.")
    except Exception as e:
        logger.error(f"Indexing failed: {e}")

if __name__ == "__main__":
    index_travel_data()

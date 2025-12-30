import os
import logging
from typing import List, Dict, Any
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from app.core.settings import settings

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge", "travel")
VECTOR_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "travel_index")

class TravelKnowledgeService:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            base_url=settings.OLLAMA_HOST,
            model="nomic-embed-text" # Using a standard embedding model
        )
        self.vector_db = None
        self._load_vector_db()

    def _load_vector_db(self):
        """Loads the vector database from disk if it exists."""
        if os.path.exists(VECTOR_DB_PATH):
            try:
                self.vector_db = FAISS.load_local(
                    VECTOR_DB_PATH, 
                    self.embeddings,
                    allow_dangerous_deserialization=True # Local file, trusted
                )
                logger.info("Travel vector DB loaded from disk.")
            except Exception as e:
                logger.error(f"Failed to load travel vector DB: {e}")
                self.vector_db = None

    def build_index(self):
        """Builds the vector index from documents in KNOWLEDGE_DIR."""
        if not os.path.exists(KNOWLEDGE_DIR):
            logger.warning(f"Knowledge directory {KNOWLEDGE_DIR} does not exist.")
            return

        logger.info(f"Building travel index from {KNOWLEDGE_DIR}...")
        
        # Load markdown files
        loader = DirectoryLoader(
            KNOWLEDGE_DIR, 
            glob="**/*.md", 
            loader_cls=TextLoader, # Using TextLoader for simplicity with MD
            show_progress=True
        )
        documents = loader.load()
        
        if not documents:
            logger.warning("No documents found to index.")
            return

        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = text_splitter.split_documents(documents)
        
        # Add prefix for nomic-embed-text
        for chunk in chunks:
            chunk.page_content = f"search_document: {chunk.page_content}"
        
        # Create vector DB
        self.vector_db = FAISS.from_documents(chunks, self.embeddings)
        
        # Save to disk
        os.makedirs(os.path.dirname(VECTOR_DB_PATH), exist_ok=True)
        self.vector_db.save_local(VECTOR_DB_PATH)
        logger.info(f"Travel index built and saved with {len(chunks)} chunks.")

    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Searches the vector DB for relevant travel information."""
        if not self.vector_db:
            logger.warning("Travel vector DB not initialized.")
            return []
            
        # Add prefix for nomic-embed-text
        formatted_query = f"search_query: {query}"
        results = self.vector_db.similarity_search_with_score(formatted_query, k=k)
        
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
            
        return formatted_results

travel_knowledge_service = TravelKnowledgeService()

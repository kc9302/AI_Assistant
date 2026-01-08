import os
import logging
from typing import List, Dict, Any
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from app.core.settings import settings
from app.agent.llm import get_embeddings

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge", "travel")
VECTOR_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "travel_index")

HASH_FILE_PATH = os.path.join(VECTOR_DB_PATH, "hash.txt")

class TravelKnowledgeService:
    def __init__(self):
        self.embeddings = get_embeddings(settings.LLM_EMBEDDING_MODEL)
        self.vector_db = None
        self._sync_index()

    def _calculate_knowledge_hash(self) -> str:
        """Calculates a hash based on the content of all files in KNOWLEDGE_DIR."""
        import hashlib
        if not os.path.exists(KNOWLEDGE_DIR):
            return ""
        
        hasher = hashlib.md5()
        # Sort files to ensure deterministic hash
        for root, _, files in sorted(os.walk(KNOWLEDGE_DIR)):
            for file in sorted(files):
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "rb") as f:
                        # Include file path and content in hash
                        hasher.update(file.encode())
                        while chunk := f.read(8192):
                            hasher.update(chunk)
        return hasher.hexdigest()

    def _get_stored_hash(self) -> str:
        """Reads the stored hash from disk."""
        if os.path.exists(HASH_FILE_PATH):
            try:
                with open(HASH_FILE_PATH, "r") as f:
                    return f.read().strip()
            except Exception:
                pass
        return ""

    def _save_hash(self, current_hash: str):
        """Saves the current hash to disk."""
        os.makedirs(os.path.dirname(HASH_FILE_PATH), exist_ok=True)
        with open(HASH_FILE_PATH, "w") as f:
            f.write(current_hash)

    def _sync_index(self):
        """Synchronizes the vector index if documents have changed or index is missing."""
        current_hash = self._calculate_knowledge_hash()
        stored_hash = self._get_stored_hash()
        index_exists = os.path.exists(VECTOR_DB_PATH)

        if not index_exists or current_hash != stored_hash:
            logger.info("Changes detected or index missing, rebuilding travel index...")
            self.build_index()
            self._save_hash(current_hash)
        else:
            logger.info("No changes detected in knowledge base, loading existing travel index.")
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
            loader_cls=TextLoader,  # Using TextLoader for simplicity with MD
            loader_kwargs={"encoding": "utf-8"},
            show_progress=True,
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

    def search(self, query: str, k: int = 3, source_filter: str | None = None) -> List[Dict[str, Any]]:
        """Searches the vector DB for relevant travel information."""
        if not self.vector_db:
            logger.warning("Travel vector DB not initialized.")
            return []
            
        # Add prefix for nomic-embed-text
        formatted_query = f"search_query: {query}"
        if source_filter:
            results = self.vector_db.similarity_search_with_score(
                formatted_query,
                k=k,
                filter={"source": source_filter},
            )
        else:
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

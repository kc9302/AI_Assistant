from pydantic_settings import BaseSettings
from pydantic import ConfigDict # Import ConfigDict

class Settings(BaseSettings):
    # Google API
    GOOGLE_API_KEY: str | None = None
    GOOGLE_CALENDAR_SCOPES: str | None = None
    
    # LLM Provider
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str
    LLM_API_KEY: str | None = None
    LLM_EMBEDDING_MODEL: str = "nomic-embed-text"
    LLM_MODEL: str = "gpt-oss:20b"
    LLM_MODEL_ROUTER: str = "gpt-oss:20b" # Default to main if not specified
    LLM_MODEL_PLANNER: str = "gpt-oss:20b"
    LLM_MODEL_EXECUTOR: str = "gpt-oss:20b"
    LLM_KEEP_ALIVE: str = "5m" # Keep in memory for 5 minutes
    
    # App
    PROJECT_NAME: str = "AI Assistant Agent"
    CHECKPOINT_DB_PATH: str = "data/checkpoints.db"
    
    model_config = ConfigDict( # Use model_config instead of Config class
        env_file = (".env", "backend/.env"),
        env_file_encoding = "utf-8",
        extra = "ignore"
    )

settings = Settings()

from pydantic_settings import BaseSettings
from pydantic import ConfigDict # Import ConfigDict

class Settings(BaseSettings):
    # Google API
    GOOGLE_API_KEY: str | None = None
    GOOGLE_CALENDAR_SCOPES: str | None = None
    
    # Ollama
    OLLAMA_HOST: str
    OLLAMA_MODEL: str = "gemma3:27b"
    OLLAMA_MODEL_PLANNER: str = "gemma3:27b"
    OLLAMA_MODEL_EXECUTOR: str = "functiongemma:ondevice"
    OLLAMA_MODEL_EXECUTOR_PATH: str = "ondevice/functiongemma-270m-it-q8_0.gguf"
    OLLAMA_KEEP_ALIVE: str = "0" # Unload immediately after use
    
    # App
    PROJECT_NAME: str = "FunctionGemma Agent"
    
    model_config = ConfigDict( # Use model_config instead of Config class
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = "ignore"
    )

settings = Settings()

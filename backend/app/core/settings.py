from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator
from typing import Self

class Settings(BaseSettings):
    # Google API
    GOOGLE_API_KEY: str | None = None
    GOOGLE_CALENDAR_SCOPES: str | None = None
   
    # LLM Provider - .env에서 필수로 설정해야 함
    LLM_PROVIDER: str
    LLM_BASE_URL: str
    LLM_API_KEY: str | None = None
    LLM_EMBEDDING_MODEL: str
    
    # Master Model Configuration - .env의 LLM_MODEL 값을 변경하면 나머지 모델들도 기본적으로 변경됨
    LLM_MODEL: str
    
    # Individual Model Overrides - 필요시 개별 모델만 다른 값으로 오버라이드 가능
    LLM_MODEL_ROUTER: str | None = None
    LLM_MODEL_PLANNER: str | None = None
    LLM_MODEL_EXECUTOR: str | None = None
    
    LLM_KEEP_ALIVE: str = "5m" # Default to 5 minutes if not in .env
    
    @model_validator(mode='after')
    def set_model_defaults(self) -> Self:
        """개별 모델이 설정되지 않았으면 LLM_MODEL을 기본값으로 사용"""
        if not self.LLM_MODEL_ROUTER:
            self.LLM_MODEL_ROUTER = self.LLM_MODEL
        if not self.LLM_MODEL_PLANNER:
            self.LLM_MODEL_PLANNER = self.LLM_MODEL
        if not self.LLM_MODEL_EXECUTOR:
            self.LLM_MODEL_EXECUTOR = self.LLM_MODEL
        return self
    
    # App
    PROJECT_NAME: str = "AI Assistant Agent"
    CHECKPOINT_DB_PATH: str = "data/checkpoints.db"
    
    model_config = ConfigDict( # Use model_config instead of Config class
        env_file = (".env", "backend/.env"),
        env_file_encoding = "utf-8",
        extra = "ignore"
    )

settings = Settings()

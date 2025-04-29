from pydantic_settings import BaseSettings
import os
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    """Server configuration settings"""
    # API settings
    APP_NAME: str = "Gemini MCP Server"
    API_VERSION: str = "v1"
    DEBUG: bool = False
    PORT: int = 8000
    
    # Google Cloud settings
    GCP_PROJECT_ID: str
    GCP_REGION: str = "us-central1"
    GCP_SERVICE_ACCOUNT_KEY: str = "credentials/vertex-ai-key.json"
    VERTEX_MODEL_NAME: str = "gemini-2.5-pro-preview-03-25"
    
    # Security and CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Performance
    WORKERS_PER_CORE: int = 1
    MAX_WORKERS: Optional[int] = None
    
    # Rate limiting
    RATE_LIMIT_RPM: int = 150  # 150 requests per minute
    ENABLE_RATE_LIMITING: bool = True
    
    # MCP protocol settings
    MAX_CONTEXT_SIZE: int = 1000000  # 1M tokens max capacity
    PREFERRED_CONTEXT_SIZE: int = 200000  # 200K tokens preferred
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from typing import Optional, List, Union, Any
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import json
from pathlib import Path

class Settings(BaseSettings):
    # API Settings
    APP_NAME: str = "Document Corroboration Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"  # ADDED - was missing
    
    # Database
    DATABASE_URL: Union[PostgresDsn, str] = Field(
        default="postgresql://postgres:postgres@localhost:5432/document_db",
        description="Database connection URL. Can be PostgreSQL or SQLite"
    )
    
    # External Services
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for GROQ service"
    )
    
    # File Processing
    MAX_FILE_SIZE: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="Maximum file size in bytes"
    )
    
    ALLOWED_EXTENSIONS: Union[str, List[str]] = Field(
        default=".pdf,.docx,.txt,.jpg,.jpeg,.png",
        description="Comma-separated list of allowed file extensions"
    )
    
    @field_validator('ALLOWED_EXTENSIONS', mode='before')
    @classmethod
    def parse_allowed_extensions(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if v.startswith('[') and v.endswith(']'):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [ext.strip() for ext in v.split(',') if ext.strip()]
        raise ValueError("ALLOWED_EXTENSIONS must be a list or comma-separated string")
    
    UPLOAD_DIR: str = Field(
        default="data/uploads",
        description="Directory to store uploaded files"
    )
    
    PROCESSED_DIR: str = Field(
        default="data/processed",
        description="Directory to store processed files"
    )
    
    # Redis
    REDIS_URL: Union[RedisDsn, str] = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True
    )

# Create settings instance
@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Create a single settings instance
settings = get_settings()
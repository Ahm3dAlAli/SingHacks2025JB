import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    APP_NAME: str = "Document Corroboration Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"  # ADDED - was missing
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/documents.db"
    
    # External Services
    GROQ_API_KEY: Optional[str] = None
    OCR_ENGINE: str = "tesseract"
    
    # File Processing
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt,.jpg,.jpeg,.png"  # CHANGED from list to str
    UPLOAD_DIR: str = "data/uploads"
    PROCESSED_DIR: str = "data/processed"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    @property
    def allowed_extensions_list(self) -> list:
        """Convert comma-separated string to list"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(',')]
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # IMPORTANT: Ignore extra fields from .env

settings = Settings()

"""
Application configuration settings.

This module handles all the configuration settings for the application,
including environment variables and default values.
"""

from typing import List, Optional, Union
from pydantic import AnyHttpUrl, validator, PostgresDsn
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application settings
    PROJECT_NAME: str = "Regulatory Ingestion Engine"
    API_V1_STR: str = "/api/v1/regulatory"
    API_PREFIX: str = "/api/v1/regulatory"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "*"
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        return v
    
    # Database
    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DATABASE_URI: Optional[PostgresDsn] = None
    
    # File storage
    DOCUMENT_STORAGE_PATH: str = "./data/documents"
    UPLOAD_DIR: str = "./data/uploads"  # Directory for file uploads
    MAX_FILE_SIZE_MB: int = 50
    
    # External services
    GROQ_API_KEY: Optional[str] = None
    
    # Add validators
    @validator("DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        
        # Convert port to integer if it's a string
        port = values.get("DB_PORT")
        if isinstance(port, str):
            try:
                port = int(port)
            except (ValueError, TypeError):
                port = 5432  # Default PostgreSQL port
        
        return str(
            PostgresDsn.build(
                scheme="postgresql",
                username=values.get("DB_USER"),
                password=values.get("DB_PASSWORD"),
                host=values.get("DB_HOST"),
                port=port or 5432,
                path=f"/{values.get('DB_NAME') or ''}",
            )
        )
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            if v.startswith("[") and v.endswith("]"):
                # Handle JSON array format
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated string
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, set)):
            return list(v)
        return []
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create settings instance
settings = Settings()

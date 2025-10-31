"""
Configuration management for TAE service using Pydantic Settings.
Loads environment variables from .env file and provides type-safe access.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # Groq API Configuration
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    # Application Configuration
    TAE_PORT: int = 8002
    LOG_LEVEL: str = "INFO"
    WORKERS: int = 4
    ENVIRONMENT: str = "development"

    # Performance Settings (Optional)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    RATE_LIMIT_PER_MINUTE: int = 100
    MAX_BATCH_SIZE: int = 1000
    BATCH_TIMEOUT_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL database URL"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to avoid repeated environment variable parsing.
    """
    return Settings()


# Create global settings instance
settings = get_settings()

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
    GROQ_MODEL: str = "llama-3.1-70b-versatile"  # Note: This model is deprecated, update to llama-3.3-70b-versatile
    GROQ_DEFAULT_TIMEOUT: int = 30
    GROQ_RETRY_DELAYS: str = "1,2,4"  # Comma-separated delays in seconds
    GROQ_RULE_PARSER_TEMPERATURE: float = 0.1
    GROQ_RULE_PARSER_MAX_TOKENS: int = 800
    GROQ_RULE_PARSER_TIMEOUT: int = 25
    GROQ_EXPLAINER_TEMPERATURE: float = 0.3
    GROQ_EXPLAINER_MAX_TOKENS: int = 1200
    GROQ_EXPLAINER_TIMEOUT: int = 25

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

    @property
    def groq_retry_delays_list(self) -> list[int]:
        """Parse GROQ_RETRY_DELAYS string into list of integers"""
        return [int(x.strip()) for x in self.GROQ_RETRY_DELAYS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to avoid repeated environment variable parsing.
    """
    return Settings()


# Create global settings instance
settings = get_settings()

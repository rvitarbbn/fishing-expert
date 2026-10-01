"""Application configuration."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/fishing_expert"

    # Redis
    redis_url: Optional[str] = None

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    # Open-Meteo
    open_meteo_base_url: str = "https://marine-api.open-meteo.com/v1/marine"

    # LLM providers (optional)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_ai_api_key: Optional[str] = None

    # Admin authentication
    admin_secret_key: str = "change-this-in-production"
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # CORS — comma-separated origins, e.g. "http://localhost:3000,https://app.example.com"
    cors_allowed_origins: Optional[str] = None

    # Logging
    log_level: str = "INFO"

    # Cache settings
    forecast_cache_ttl_seconds: int = 3600
    recommendation_cache_ttl_seconds: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

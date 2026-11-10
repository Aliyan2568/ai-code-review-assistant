"""Application settings loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Code Review Assistant"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read the environment once)."""
    return Settings()

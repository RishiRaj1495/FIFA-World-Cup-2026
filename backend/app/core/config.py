"""
Application configuration.

All tunables are pulled from environment variables so the same codebase
can move from a laptop to a stadium ops server without code changes.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Stadium Fan Concierge API"
    environment: str = "development"

    # Anthropic API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    ai_max_tokens: int = 600
    ai_request_timeout_seconds: int = 20

    # CORS
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5500,http://localhost:5500"

    # Crowd simulation
    crowd_refresh_seconds: int = 15

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so .env is parsed only once per process."""
    return Settings()

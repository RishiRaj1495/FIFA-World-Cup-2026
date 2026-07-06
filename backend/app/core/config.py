"""
Application configuration.

Deliberately minimal: this application has no external service
dependencies and no secrets, so there is nothing sensitive to configure.
The only tunables are operational (CORS origins), pulled from environment
variables so the same codebase can move from a laptop to a hosted
deployment without code changes.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Stadium Fan Concierge API"
    environment: str = "development"

    # CORS — comma-separated list of allowed frontend origins.
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5500,http://localhost:5500"

    # Crowd simulation refresh cadence, in seconds (used by the frontend polling interval).
    crowd_refresh_seconds: int = 15

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so environment variables are read only once per process."""
    return Settings()

"""Application configuration with cybersecurity validation using Pydantic Settings."""

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration class loading values from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General App Settings
    APP_NAME: str = Field(default="Traffic Fines B2B Monitor SaaS")
    APP_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Cybersecurity & Authentication
    SECRET_KEY: str = Field(
        default="insecure-default-change-in-production-0123456789abcdef",
        description="Cryptographic secret key for signing tokens",
    )
    API_KEY_HEADER_NAME: str = Field(default="X-API-Key")
    ADMIN_API_KEY: str = Field(
        default="dev-admin-secure-api-key-replace-in-prod",
        description="Master administrative API Key",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # CORS
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    # Scraping & External Fine Provider Settings
    SCRAPER_REQUEST_TIMEOUT_SECONDS: int = Field(default=15)
    SCRAPER_MAX_RETRIES: int = Field(default=3)
    SCRAPER_USER_AGENT: str = Field(
        default="FleetMonitorBot/1.0 (+https://finesmonitor.example.com/bot)"
    )

    # Security Headers
    ENABLE_HSTS: bool = Field(default=True)
    CONTENT_SECURITY_POLICY: str = Field(
        default="default-src 'none'; frame-ancestors 'none';"
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = {"development", "staging", "production", "testing"}
        if v.lower() not in valid_envs:
            raise ValueError(f"ENVIRONMENT must be one of {valid_envs}")
        return v.lower()

    @property
    def cors_origins(self) -> List[str]:
        """Convert comma-separated allowed origins to a typed list."""
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()

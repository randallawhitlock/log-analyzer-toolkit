"""
Unified configuration using pydantic-settings.

All application settings are defined here and can be overridden via
environment variables or a .env file. Other modules should import
the ``settings`` singleton rather than reading env vars directly.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_version: str = "1.0.1"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./log_analyzer.db"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # Rate limiting
    rate_limit_default: str = "60/minute"

    # Upload
    max_upload_size_mb: int = 100

    # Analysis
    default_max_errors: int = 100
    max_errors_limit: int = 1000
    min_errors_limit: int = 1
    default_triage_max_errors: int = 50

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    min_page_size: int = 1

    # Upload directory
    upload_directory: str = "./uploads"

    # Auth - empty string means dev mode (no auth required)
    api_key: str = ""

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve project root where .env is stored
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Core application settings loaded from environment variables or defaults."""

    model_config = SettingsConfigDict(
        env_file=[".env", str(PROJECT_ROOT / ".env")],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "RepoDefense API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins for web clients",
    )
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://repouser:repopassword@localhost:5432/repodefense",
        description="Database connection URL",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    SUPABASE_URL: str = Field(
        default="https://localhost.supabase.co",
        description="Supabase project URL",
    )
    SUPABASE_ANON_KEY: str = Field(
        default="anon-key-placeholder",
        description="Supabase anon public API key",
    )
    SUPABASE_JWT_SECRET: str = Field(
        default="development-supabase-jwt-secret-min-32-chars-long",
        description="Supabase JWT secret for validating user tokens",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm used for verifying Supabase JWT tokens",
    )


settings = Settings()

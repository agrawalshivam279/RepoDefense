import ipaddress
from pathlib import Path
from urllib.parse import urlparse

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

    # LLM Settings (LiteLLM with FreeLLMAPI)
    FREELLMAPI_BASE_URL: str = Field(
        default="http://127.0.0.1:31415/v1",
        description="FreeLLMAPI or OpenAI-compatible base URL",
    )
    FREELLMAPI_API_KEY: str = Field(
        default="",
        description="API key for FreeLLMAPI / OpenAI-compatible endpoint",
    )
    ALLOWED_LLM_BASE_HOSTS: list[str] = Field(
        default_factory=lambda: [
            "api.openai.com",
            "api.groq.com",
            "api.anthropic.com",
            "generativelanguage.googleapis.com",
            "openrouter.ai",
            "api.together.xyz",
        ],
        description="Approved HTTPS hostnames for caller-supplied LLM base_url overrides",
    )
    LLM_MODEL: str = Field(
        default="openai/auto",
        description="LiteLLM model identifier",
    )
    LLM_TIMEOUT_SECONDS: float = Field(
        default=30.0,
        description="Timeout in seconds for LLM generation requests",
    )
    LLM_MAX_RETRIES: int = Field(
        default=2,
        description="Maximum retry attempts on transient LLM failures",
    )


settings = Settings()


def validate_llm_base_url(base_url: str | None) -> str | None:
    """Validate optional caller-supplied LLM base URL against approved HTTPS hosts."""
    if base_url is None:
        return None
    cleaned = base_url.strip()
    if not cleaned:
        raise ValueError("LLM base_url override cannot be empty")
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() != "https":
        raise ValueError("LLM base_url override must use HTTPS")
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError("LLM base_url override must use a valid hostname without credentials")
    host = parsed.hostname.lower()
    is_ip = True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        is_ip = False
    if is_ip:
        raise ValueError("LLM base_url override cannot target an IP address")
    allowed = {h.strip().lower() for h in settings.ALLOWED_LLM_BASE_HOSTS if h.strip()}
    srv = urlparse(settings.FREELLMAPI_BASE_URL)
    if srv.scheme.lower() == "https" and srv.hostname:
        allowed.add(srv.hostname.lower())
    if host not in allowed:
        raise ValueError(f"LLM base_url host '{host}' is not in the approved provider allowlist")
    return cleaned

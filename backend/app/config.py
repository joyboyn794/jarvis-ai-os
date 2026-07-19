"""
Jarvis Configuration — Pydantic Settings

All application configuration is loaded from environment variables
with sensible defaults. Uses pydantic-settings for validation.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────
    APP_NAME: str = "Jarvis"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me"
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://jarvis:jarvis_secret@localhost:5432/jarvis"
    DATABASE_URL_SYNC: str = "postgresql://jarvis:jarvis_secret@localhost:5432/jarvis"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── OpenAI ───────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7

    # ── Voice ────────────────────────────────────────
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    TTS_PROVIDER: str = "openai"  # openai | elevenlabs | edge
    TTS_VOICE: str = "alloy"
    ELEVENLABS_API_KEY: str = ""

    # ── Authentication ───────────────────────────────
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Security ─────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    MAX_REQUEST_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Logging ──────────────────────────────────────
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "json"

    # ── Monitoring ───────────────────────────────────
    ENABLE_METRICS: bool = True
    SENTRY_DSN: str = ""


settings = Settings()

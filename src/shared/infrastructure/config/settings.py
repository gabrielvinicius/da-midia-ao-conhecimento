"""Application Configuration."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    # Application
    app_name: str = "video-summarizer"
    app_env: str = "development"
    debug: bool = False
    LIGHTWEIGHT_BOOTSTRAP: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./app.db"
    db_echo: bool = False

    # Security
    secret_key: str = "insecure-secret-key-for-dev"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    auth_password_min_length: int = 8

    # RabbitMQ / Celery
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: Optional[str] = None

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "video-summarizer"
    minio_secure: bool = False

    # Providers (global defaults only; per-context allowlists live in each context)
    transcription_default_provider: str = "whisper"
    summarization_default_provider: str = "openai"
    sentiment_default_provider: str = "vader"
    topic_modeling_default_provider: str = "bertopic"

    @property
    def sync_database_url(self) -> str:
        if "aiosqlite" in self.database_url:
            return self.database_url.replace("+aiosqlite", "")
        return self.database_url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv(override=True)

class Settings:
    # PostgreSQL Database
    DB_SCHEME: str = os.getenv("DB_SCHEME", "postgresql+asyncpg")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "video_summarizer")

    # Authentication (JWT)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_strong_and_long_secret_key_should_be_placed_here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    # Storage Provider
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")

    # S3 / MinIO Settings
    BUCKET_NAME: str = os.getenv("BUCKET_NAME", "videos")
    ENDPOINT_URL: str = os.getenv("ENDPOINT_URL", "http://localhost:9000")
    ACCESS_KEY: str = os.getenv("ACCESS_KEY", "minio")
    SECRET_KEY_S3: str = os.getenv("SECRET_KEY_S3", "minio123")

    # LLM Providers
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "huggingface")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    TRANSFORMERS_MODEL: str = os.getenv("TRANSFORMERS_MODEL", "facebook/bart-large-cnn")

    # Redis / Celery Broker
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

    # Video Upload Settings
    VIDEO_ALLOWED_EXTENSIONS: Optional[str] = os.getenv("VIDEO_ALLOWED_EXTENSIONS", ".mp4,.mov,.avi,.mkv,.webm")
    VIDEO_MAX_FILE_SIZE_MB: Optional[int] = int(os.getenv("VIDEO_MAX_FILE_SIZE_MB", 200))

    # Analytics Settings
    ANALYTICS_DEFAULT_TRANSCRIPTION_FACTOR: Optional[float] = float(os.getenv("ANALYTICS_DEFAULT_TRANSCRIPTION_FACTOR", 1.0))
    ANALYTICS_DEFAULT_SUMMARIZATION_SECONDS: Optional[float] = float(os.getenv("ANALYTICS_DEFAULT_SUMMARIZATION_SECONDS", 60.0))
    ANALYTICS_HIGH_CONFIDENCE_THRESHOLD: Optional[int] = int(os.getenv("ANALYTICS_HIGH_CONFIDENCE_THRESHOLD", 10))

    # Notification Settings (SMTP for Email)
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST", "smtp.mailtrap.io")
    SMTP_PORT: Optional[int] = int(os.getenv("SMTP_PORT", 2525))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", "your_mailtrap_user")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD", "your_mailtrap_password")

    # Observability (Jaeger for Tracing)
    JAEGER_AGENT_HOST: Optional[str] = os.getenv("JAEGER_AGENT_HOST", "localhost")
    JAEGER_AGENT_PORT: Optional[int] = int(os.getenv("JAEGER_AGENT_PORT", 6831))

    @property
    def database_url(self) -> str:
        return f"{self.DB_SCHEME}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")

settings = Settings()

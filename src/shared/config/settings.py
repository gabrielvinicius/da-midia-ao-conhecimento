import json
import os
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

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

    # Authentication (JWT & Security)
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.getenv("AUTH_SECRET_KEY", "a_very_strong_and_long_secret_key_should_be_placed_here"))
    ALGORITHM: str = os.getenv("ALGORITHM", os.getenv("AUTH_JWT_ALGORITHM", "HS256"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    
    AUTH_PASSWORD_MIN_LENGTH: int = int(os.getenv("AUTH_PASSWORD_MIN_LENGTH", "8"))
    AUTH_COOKIE_SECURE: bool = os.getenv("AUTH_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    AUTH_COOKIE_SAMESITE: str = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
    AUTH_ALLOWED_ORIGINS: Tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("AUTH_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )

    # Storage Provider
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")

    # S3 / MinIO Settings
    BUCKET_NAME: str = os.getenv("BUCKET_NAME", "videos")
    ENDPOINT_URL: str = os.getenv("ENDPOINT_URL", "http://localhost:9000")
    ACCESS_KEY: str = os.getenv("ACCESS_KEY", "minio")
    SECRET_KEY_S3: str = os.getenv("SECRET_KEY_S3", "minio123")

    # Media Processing Limits
    # Default: 500MB (aligned with previous MediaSettings)
    MEDIA_MAX_FILE_SIZE_BYTES: int = int(os.getenv("MEDIA_MAX_FILE_SIZE_BYTES", 500 * 1024 * 1024))
    MEDIA_MIN_FILE_SIZE_BYTES: int = 1
    
    # Legacy support for MB env var
    _legacy_mb_limit = os.getenv("VIDEO_MAX_FILE_SIZE_MB")
    if _legacy_mb_limit:
        MEDIA_MAX_FILE_SIZE_BYTES = int(_legacy_mb_limit) * 1024 * 1024

    # Allowed Extensions
    MEDIA_ALLOWED_VIDEO_EXTENSIONS: Tuple[str, ...] = tuple(
        ext.strip() for ext in os.getenv("MEDIA_ALLOWED_VIDEO_EXTENSIONS", "mp4,avi,mov,mkv,webm,flv").split(",")
    )
    MEDIA_ALLOWED_AUDIO_EXTENSIONS: Tuple[str, ...] = tuple(
        ext.strip() for ext in os.getenv("MEDIA_ALLOWED_AUDIO_EXTENSIONS", "mp3,wav,flac,aac,ogg,m4a").split(",")
    )
    MEDIA_ALLOWED_TEXT_EXTENSIONS: Tuple[str, ...] = tuple(
        ext.strip() for ext in os.getenv("MEDIA_ALLOWED_TEXT_EXTENSIONS", "txt,pdf,doc,docx").split(",")
    )

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

    # Topic Modeling Providers
    TOPIC_MODELING_ENABLED_PROVIDERS: str = os.getenv(
        "TOPIC_MODELING_ENABLED_PROVIDERS",
        "sklearn_lda,sklearn_lsa,sklearn_nmf,keyword_frequency,bertopic",
    )
    TOPIC_MODELING_DEFAULT_PROVIDER: str = os.getenv(
        "TOPIC_MODELING_DEFAULT_PROVIDER",
        "sklearn_lda",
    )
    TOPIC_MODELING_PLUGIN_MODULES: str = os.getenv(
        "TOPIC_MODELING_PLUGIN_MODULES",
        "",
    )
    TOPIC_MODELING_PROVIDER_OVERRIDES: str = os.getenv(
        "TOPIC_MODELING_PROVIDER_OVERRIDES",
        "{}",
    )

    # Summarization Providers
    SUMMARIZATION_ENABLED_PROVIDERS: str = os.getenv(
        "SUMMARIZATION_ENABLED_PROVIDERS",
        "all",
    )
    SUMMARIZATION_DEFAULT_PROVIDER: str = os.getenv(
        "SUMMARIZATION_DEFAULT_PROVIDER",
        "heuristic_interpretive",
    )
    SUMMARIZATION_PLUGIN_MODULES: str = os.getenv(
        "SUMMARIZATION_PLUGIN_MODULES",
        "",
    )
    SUMMARIZATION_PROVIDER_OVERRIDES: str = os.getenv(
        "SUMMARIZATION_PROVIDER_OVERRIDES",
        "{}",
    )

    # Sentiment Providers
    SENTIMENT_ENABLED_PROVIDERS: str = os.getenv(
        "SENTIMENT_ENABLED_PROVIDERS",
        "transformers,vader",
    )
    SENTIMENT_DEFAULT_PROVIDER: str = os.getenv(
        "SENTIMENT_DEFAULT_PROVIDER",
        "transformers",
    )
    SENTIMENT_PLUGIN_MODULES: str = os.getenv(
        "SENTIMENT_PLUGIN_MODULES",
        "",
    )
    SENTIMENT_PROVIDER_OVERRIDES: str = os.getenv(
        "SENTIMENT_PROVIDER_OVERRIDES",
        "{}",
    )

    @property
    def database_url(self) -> str:
        return f"{self.DB_SCHEME}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    @property
    def topic_modeling_enabled_list(self) -> List[str]:
        return [p.strip() for p in self.TOPIC_MODELING_ENABLED_PROVIDERS.split(",") if p.strip()]

    @property
    def topic_modeling_plugin_modules(self) -> List[str]:
        return [p.strip() for p in self.TOPIC_MODELING_PLUGIN_MODULES.split(",") if p.strip()]

    @property
    def topic_modeling_provider_overrides(self) -> Dict[str, Dict[str, Any]]:
        try:
            parsed = json.loads(self.TOPIC_MODELING_PROVIDER_OVERRIDES)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {}

    @property
    def summarization_enabled_list(self) -> List[str]:
        values = [p.strip() for p in self.SUMMARIZATION_ENABLED_PROVIDERS.split(",") if p.strip()]
        if not values or any(v.lower() == "all" for v in values):
            return []
        return values

    @property
    def summarization_plugin_modules(self) -> List[str]:
        return [p.strip() for p in self.SUMMARIZATION_PLUGIN_MODULES.split(",") if p.strip()]

    @property
    def summarization_provider_overrides(self) -> Dict[str, Dict[str, Any]]:
        try:
            parsed = json.loads(self.SUMMARIZATION_PROVIDER_OVERRIDES)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {}

    @property
    def sentiment_enabled_list(self) -> List[str]:
        return [p.strip() for p in self.SENTIMENT_ENABLED_PROVIDERS.split(",") if p.strip()]

    @property
    def sentiment_plugin_modules(self) -> List[str]:
        return [p.strip() for p in self.SENTIMENT_PLUGIN_MODULES.split(",") if p.strip()]

    @property
    def sentiment_provider_overrides(self) -> Dict[str, Dict[str, Any]]:
        try:
            parsed = json.loads(self.SENTIMENT_PROVIDER_OVERRIDES)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {}

    # Compatibility Properties for AuthSettings migration
    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY

    @property
    def algorithm(self) -> str:
        return self.ALGORITHM

    @property
    def access_token_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def password_min_length(self) -> int:
        return self.AUTH_PASSWORD_MIN_LENGTH

    @property
    def allowed_cors_origins(self) -> Tuple[str, ...]:
        return self.AUTH_ALLOWED_ORIGINS

    @property
    def cookie_secure(self) -> bool:
        return self.AUTH_COOKIE_SECURE

    @property
    def cookie_samesite(self) -> str:
        return self.AUTH_COOKIE_SAMESITE

settings = Settings()
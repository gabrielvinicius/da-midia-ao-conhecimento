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

    # Hugging Face
    hf_token: Optional[str] = None

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "video-summarizer"
    minio_secure: bool = False

    # Providers (global defaults only; per-context allowlists live in each context)
    transcription_default_provider: str = "fastwhisper"
    summarization_default_provider: str = "ollama"
    sentiment_default_provider: str = "vader"
    topic_modeling_default_provider: str = "bertopic"

    # Ollama (LLM local): endereço do servidor e modelos padrão
    ollama_host: str = "http://localhost:11434"
    llm_model: str = "qwen3.5:9b"
    llm_fallback_model: str = "gemma4:e4b"
    llm_context_tokens: int = 32768
    llm_timeout_seconds: int = 900
    # Descrição de quadros de vídeo: "moondream" (padrão) ou "ollama"
    # (usa o modelo multimodal definido em visual_ollama_model).
    visual_provider: str = "moondream"
    visual_ollama_model: str = "qwen3.5:9b"

    # AI / Machine Learning Hardware
    # Options: "auto", "cuda", "cpu", "rocm"
    ai_device: str = "auto"
    # Options: "float16", "float32", "int8", "int8_float16"
    ai_compute_type: str = "default"

    @property
    def resolved_device(self) -> str:
        """Determines the actual device to use based on settings and hardware."""
        import torch
        if self.ai_device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            # ROCm typically maps to 'cuda' in torch if properly installed
            return "cpu"
        return self.ai_device

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

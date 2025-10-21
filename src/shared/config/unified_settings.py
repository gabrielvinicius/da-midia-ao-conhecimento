"""
Unified settings - eliminating config duplication
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./app.db"))
    echo: bool = field(default_factory=lambda: os.getenv("DB_ECHO", "false").lower() == "true")
    pool_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "5")))

@dataclass 
class StorageConfig:
    """Storage configuration"""
    provider: str = field(default_factory=lambda: os.getenv("STORAGE_PROVIDER", "local"))
    root_path: str = field(default_factory=lambda: os.getenv("STORAGE_ROOT", "storage"))
    
    # S3 settings (only used if provider=s3)
    bucket_name: str = field(default_factory=lambda: os.getenv("S3_BUCKET_NAME", ""))
    access_key: str = field(default_factory=lambda: os.getenv("S3_ACCESS_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("S3_SECRET_KEY", ""))
    endpoint_url: Optional[str] = field(default_factory=lambda: os.getenv("S3_ENDPOINT_URL"))

@dataclass
class ProcessingConfig:
    """Processing limits and settings for all modules"""
    # File limits
    max_file_size: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", str(100 * 1024 * 1024))))  # 100MB
    min_file_size: int = field(default_factory=lambda: int(os.getenv("MIN_FILE_SIZE", "1024")))  # 1KB
    
    # Text limits
    max_text_length: int = field(default_factory=lambda: int(os.getenv("MAX_TEXT_LENGTH", "50000")))
    min_text_length: int = field(default_factory=lambda: int(os.getenv("MIN_TEXT_LENGTH", "10")))
    
    # Processing timeouts
    processing_timeout: int = field(default_factory=lambda: int(os.getenv("PROCESSING_TIMEOUT", "300")))  # 5 min
    retry_attempts: int = field(default_factory=lambda: int(os.getenv("RETRY_ATTEMPTS", "3")))
    
    # Supported languages (common across all modules)
    supported_languages: set = field(default_factory=lambda: set(
        os.getenv("SUPPORTED_LANGUAGES", "en,es,fr,de,it,pt,ru,zh,ja,ko").split(",")
    ))

@dataclass
class RedisConfig:
    """Redis configuration for caching and queues"""
    url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    cache_ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL", "3600")))  # 1 hour

@dataclass
class APIConfig:
    """API configuration"""
    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    cors_origins: list = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))

@dataclass
class UnifiedSettings:
    """Single settings class for entire application"""
    
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    api: APIConfig = field(default_factory=APIConfig)
    
    # Environment
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "your-secret-key-here"))
    
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """Get configuration specific to a module"""
        base_config = {
            "max_file_size": self.processing.max_file_size,
            "min_file_size": self.processing.min_file_size,
            "processing_timeout": self.processing.processing_timeout,
            "retry_attempts": self.processing.retry_attempts,
            "supported_languages": self.processing.supported_languages,
            "storage_provider": self.storage.provider,
            "cache_ttl": self.redis.cache_ttl,
        }
        
        # Module-specific overrides can be added here
        module_overrides = {
            "transcription": {
                "max_audio_duration": int(os.getenv("MAX_AUDIO_DURATION", "3600")),  # 1 hour
            },
            "summarization": {
                "max_summary_length": int(os.getenv("MAX_SUMMARY_LENGTH", "1000")),
                "min_text_for_summary": int(os.getenv("MIN_TEXT_FOR_SUMMARY", "100")),
            },
            "topic_modeling": {
                "max_topics": int(os.getenv("MAX_TOPICS", "10")),
                "min_topic_coherence": float(os.getenv("MIN_TOPIC_COHERENCE", "0.3")),
            }
        }
        
        if module_name in module_overrides:
            base_config.update(module_overrides[module_name])
        
        return base_config
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"

# Global settings instance
settings = UnifiedSettings()

def get_settings() -> UnifiedSettings:
    """Get global settings instance"""
    return settings
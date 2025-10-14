# src/media_management/config/settings.py
from pydantic_settings import BaseSettings
from typing import List

class MediaSettings(BaseSettings):
    """Media management settings."""
    
    # File upload settings
    max_file_size_mb: int = 200
    allowed_extensions: List[str] = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav"]
    
    # Default providers
    default_storage_provider: str = "local"
    default_transcription_provider: str = "whisper"
    default_summarization_provider: str = "huggingface"
    
    class Config:
        env_prefix = "MEDIA_"
        case_sensitive = False
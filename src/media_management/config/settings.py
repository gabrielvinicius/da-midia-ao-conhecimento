from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class MediaSettings(BaseSettings):
    """Media-management specific settings."""

    storage_providers_allowed: List[str] = ["local", "s3"]
    transcription_providers_allowed: List[str] = [
        "whisper",
        "fastwhisper",
        "mock",
        "mock_whisper",
    ]
    summarization_providers_allowed: List[str] = ["ollama", "mock"]
    sentiment_providers_allowed: List[str] = ["vader", "transformers", "mock"]
    topic_providers_allowed: List[str] = ["bertopic", "mock"]
    media_min_file_size_bytes: int = 1
    media_max_file_size_bytes: int = 500 * 1024 * 1024
    media_allowed_audio_extensions: List[str] = [
        "mp3",
        "wav",
        "flac",
        "aac",
        "ogg",
        "m4a",
    ]
    media_allowed_video_extensions: List[str] = [
        "mp4",
        "avi",
        "mov",
        "mkv",
        "webm",
        "flv",
    ]
    media_allowed_text_extensions: List[str] = [
        "txt",
        "pdf",
        "doc",
        "docx",
        "png",
        "jpg",
        "jpeg",
        "tiff",
        "bmp",
    ]

    model_config = SettingsConfigDict(
        env_prefix="MEDIA_",
        case_sensitive=False,
        extra="ignore",
    )


media_settings = MediaSettings()


__all__ = ["MediaSettings", "media_settings"]

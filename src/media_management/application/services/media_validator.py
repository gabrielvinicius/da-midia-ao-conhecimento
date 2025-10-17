# src/media_management/application/services/media_validator.py
import os
from src.media_management.domain.media import MediaType
from src.media_management.application.config.settings import MediaSettings


class MediaValidator:
    def __init__(self, settings: MediaSettings):
        self.settings = settings

    def validate(self, file: bytes, filename: str) -> None:
        if not filename:
            raise ValueError("File must have a filename.")
        if not file:
            raise ValueError("File content is empty.")

        self._validate_file_type(filename)
        self._validate_file_size(file)

    def _validate_file_type(self, filename: str) -> None:
        _, ext = os.path.splitext(filename or "")
        ext = ext.lower()
        supported = (
            ext in self.settings.video_extensions
            or ext in self.settings.audio_extensions
            or ext in self.settings.text_extensions
        )
        if not supported:
            raise ValueError(f"Unsupported file type: {ext}")

    def _validate_file_size(self, file: bytes) -> None:
        if len(file) > self.settings.max_file_size_bytes:
            raise ValueError(f"File too large. Max size is {self.settings.max_file_size_mb}MB")

    def get_media_type(self, filename: str) -> MediaType:
        _, ext = os.path.splitext(filename or "")
        ext = ext.lower()
        if ext in self.settings.video_extensions:
            return MediaType.VIDEO
        if ext in self.settings.audio_extensions:
            return MediaType.AUDIO
        if ext in self.settings.text_extensions:
            return MediaType.TEXT
        # This should not be reached if validate() is called first
        raise ValueError(f"Cannot determine media type for: {ext}")

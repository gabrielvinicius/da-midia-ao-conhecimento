"""Reusable validator for upload constraints in media management."""

from src.media_management.config.settings import MediaSettings


class MediaUploadValidator:
    """Validates upload payloads according to configured constraints."""

    def __init__(self, settings: MediaSettings):
        self._settings = settings

    def validate(self, file_content: bytes, filename: str) -> None:
        """Validate that the file content and name respect the constraints."""

        if not file_content:
            raise ValueError("File content is empty")

        content_length = len(file_content)
        if content_length < self._settings.min_file_size_bytes:
            raise ValueError("File size is too small")

        if content_length > self._settings.max_file_size_bytes:
            raise ValueError("File size exceeds maximum limit")

        if not filename:
            raise ValueError("Filename is required to determine media type")

        extension = filename.lower().rsplit(".", maxsplit=1)
        if len(extension) != 2:
            raise ValueError("Unsupported file format")

        ext = extension[1]
        if ext not in set(self._settings.allowed_audio_extensions) and ext not in set(
            self._settings.allowed_video_extensions
        ):
            raise ValueError("Unsupported file format")

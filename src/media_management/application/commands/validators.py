"""Reusable validator for upload constraints in media management."""

from src.shared.infrastructure.config.settings import Settings


class MediaUploadValidator:
    """Validates upload payloads according to configured constraints."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def validate(self, file_content: bytes, filename: str) -> None:
        """Validate that the file content and name respect the constraints."""
        if not file_content:
            raise ValueError("File content is empty")

        content_length = len(file_content)
        if content_length < self._settings.MEDIA_MIN_FILE_SIZE_BYTES:
            raise ValueError("File size is too small")

        if content_length > self._settings.MEDIA_MAX_FILE_SIZE_BYTES:
            raise ValueError("File size exceeds maximum limit")

        if not filename:
            raise ValueError("Filename is required to determine media type")

        extension = filename.lower().rsplit(".", maxsplit=1)
        if len(extension) != 2:
            raise ValueError("Unsupported file format")

        ext = extension[1]
        allowed_extensions = (
            set(self._settings.MEDIA_ALLOWED_AUDIO_EXTENSIONS)
            | set(self._settings.MEDIA_ALLOWED_VIDEO_EXTENSIONS)
            | set(self._settings.MEDIA_ALLOWED_TEXT_EXTENSIONS)
        )

        if ext not in allowed_extensions:
            raise ValueError("Unsupported file format")
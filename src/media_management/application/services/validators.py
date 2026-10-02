"""Reusable validator for upload constraints in media management."""

from src.media_management.application.errors import InvalidUploadError
from src.media_management.config.settings import MediaSettings


class MediaUploadValidator:
    """Validates upload payloads according to configured constraints."""

    def __init__(self, settings: MediaSettings):
        self._settings = settings

    def validate(self, file_content: bytes, filename: str) -> None:
        """Validate that the file content and name respect the constraints."""
        if not file_content:
            raise InvalidUploadError("Conteúdo do arquivo está vazio")

        content_length = len(file_content)
        if content_length < self._settings.media_min_file_size_bytes:
            raise InvalidUploadError("Tamanho do arquivo é muito pequeno")

        if content_length > self._settings.media_max_file_size_bytes:
            raise InvalidUploadError("Tamanho do arquivo excede o limite máximo")

        if not filename:
            raise InvalidUploadError("Nome do arquivo é obrigatório para determinar o tipo")

        extension = filename.lower().rsplit(".", maxsplit=1)
        if len(extension) != 2:
            raise InvalidUploadError("Formato de arquivo não suportado")

        ext = extension[1]
        allowed_extensions = (
            set(self._settings.media_allowed_audio_extensions)
            | set(self._settings.media_allowed_video_extensions)
            | set(self._settings.media_allowed_text_extensions)
        )

        if ext not in allowed_extensions:
            raise InvalidUploadError("Formato de arquivo não suportado")

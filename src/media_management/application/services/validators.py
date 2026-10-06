"""Regras do arquivo enviado: tamanho e extensão."""

from src.media_management.application.errors import InvalidUploadError
from src.media_management.config.settings import MediaSettings


class MediaUploadValidator:
    """Valida o envio pelos limites da configuração (MEDIA_MAX_FILE_SIZE_BYTES etc.).

    Antes havia um segundo validador de tamanho, com o limite fixo no código.
    """

    def __init__(self, settings: MediaSettings):
        self._settings = settings

    @property
    def max_size_bytes(self) -> int:
        return self._settings.media_max_file_size_bytes

    def validate(self, size_bytes: int, filename: str) -> None:
        if not size_bytes:
            raise InvalidUploadError("Conteúdo do arquivo está vazio")
        if size_bytes < self._settings.media_min_file_size_bytes:
            raise InvalidUploadError("Tamanho do arquivo é muito pequeno")
        if size_bytes > self.max_size_bytes:
            raise InvalidUploadError("Tamanho do arquivo excede o limite máximo")
        if not filename:
            raise InvalidUploadError("Nome do arquivo é obrigatório para determinar o tipo")
        extension = filename.lower().rsplit(".", maxsplit=1)
        if len(extension) != 2:
            raise InvalidUploadError("Formato de arquivo não suportado")
        allowed = (
            set(self._settings.media_allowed_audio_extensions)
            | set(self._settings.media_allowed_video_extensions)
            | set(self._settings.media_allowed_text_extensions)
        )
        if extension[1] not in allowed:
            raise InvalidUploadError("Formato de arquivo não suportado")

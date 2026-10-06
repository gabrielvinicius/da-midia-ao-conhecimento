from src.shared.domain.errors import DomainError, TemporarilyUnavailableError


class MediaDataErasureError(TemporarilyUnavailableError):
    """Um módulo não conseguiu apagar os dados que derivou da mídia (503)."""


class InvalidRangeError(DomainError):
    """Cabeçalho Range inválido ou fora do arquivo (416)."""


class InvalidUploadError(DomainError):
    """Arquivo enviado vazio, fora dos limites de tamanho ou de formato não aceito (400)."""

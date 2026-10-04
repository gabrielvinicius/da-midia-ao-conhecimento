from enum import Enum


class MediaType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"


class MediaStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"  # transcrição ou extração do texto
    ANALYZING = "analyzing"  # texto pronto, análise em andamento
    COMPLETED = "completed"  # análise concluída
    FAILED = "failed"


# Mídias com trabalho em andamento (painel e alertas de fila).
IN_PROGRESS_STATUSES = frozenset({MediaStatus.PROCESSING, MediaStatus.ANALYZING})

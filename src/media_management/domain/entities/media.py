from __future__ import annotations

import datetime
from typing import Optional
from uuid import UUID

from src.media_management.domain.enums import MediaStatus, MediaType
from src.shared.domain.base_entity import BaseEntity
from src.shared.domain.errors import ConflictError
from src.shared.domain.time.clock import utcnow


class MediaNotReprocessableError(ConflictError):
    """A mídia não está em um estado que permita reprocessamento."""


class InvalidMediaTransitionError(ConflictError):
    """Mudança de estado que o ciclo de vida da mídia não permite.

    Acontece com eventos atrasados ou repetidos: uma transcrição que termina
    depois de a mídia ter sido dada como parada, por exemplo.
    """


# Ciclo de vida: enviada → processando (texto) → analisando → concluída.
# Qualquer etapa pode falhar; só uma mídia com falha volta a processar
# (reprocessamento). Repetir o estado atual é aceito (eventos repetidos).
# Uma análise que termina depois do prazo ainda conclui a mídia: o resultado
# existe e foi gravado.
_TRANSITIONS: dict[MediaStatus, frozenset[MediaStatus]] = {
    MediaStatus.UPLOADED: frozenset({MediaStatus.PROCESSING, MediaStatus.ANALYZING, MediaStatus.FAILED}),
    MediaStatus.PROCESSING: frozenset({MediaStatus.ANALYZING, MediaStatus.FAILED}),
    MediaStatus.ANALYZING: frozenset({MediaStatus.COMPLETED, MediaStatus.FAILED}),
    MediaStatus.COMPLETED: frozenset(),
    MediaStatus.FAILED: frozenset({MediaStatus.PROCESSING, MediaStatus.COMPLETED}),
}


class Media(BaseEntity):
    """Media aggregate root."""

    user_id: UUID
    filename: str
    file_size_bytes: int
    mime_type: Optional[str]
    duration: Optional[int]
    media_type: MediaType
    storage_provider: str
    original_file_path: str
    status: MediaStatus
    transcription_provider: Optional[str]
    language: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    error_message: Optional[str] = None

    def __init__(
        self,
        media_id: UUID,
        user_id: UUID,
        filename: str,
        file_size_bytes: int,
        mime_type: Optional[str],
        duration: Optional[int],
        media_type: MediaType,
        storage_provider: str,
        original_file_path: str,
        status: MediaStatus = MediaStatus.UPLOADED,
        transcription_provider: Optional[str] = None,
        language: str = "auto",
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        error_message: Optional[str] = None,
    ):
        super().__init__(media_id)
        self.user_id = user_id
        self.filename = filename
        self.file_size_bytes = file_size_bytes
        self.mime_type = mime_type
        self.duration = duration
        self.media_type = media_type
        self.storage_provider = storage_provider
        self.original_file_path = original_file_path
        self.status = status
        self.transcription_provider = transcription_provider
        self.language = language
        self.created_at = created_at or utcnow()
        self.updated_at = updated_at or utcnow()
        self.error_message = error_message

    @classmethod
    def create(
        cls,
        media_id: UUID,
        user_id: UUID,
        filename: str,
        file_size_bytes: int,
        media_type: MediaType,
        storage_provider: str,
        original_file_path: str,
        mime_type: Optional[str] = None,
        duration: Optional[int] = None,
        transcription_provider: Optional[str] = None,
        language: str = "auto",
    ) -> Media:
        return cls(
            media_id=media_id,
            user_id=user_id,
            filename=filename,
            file_size_bytes=file_size_bytes,
            media_type=media_type,
            storage_provider=storage_provider,
            original_file_path=original_file_path,
            mime_type=mime_type,
            duration=duration,
            transcription_provider=transcription_provider,
            language=language,
        )

    def can_change_to(self, status: MediaStatus) -> bool:
        return status == self.status or status in _TRANSITIONS[self.status]

    def _change_to(self, status: MediaStatus, error_message: Optional[str] = None) -> None:
        if not self.can_change_to(status):
            raise InvalidMediaTransitionError(
                f"A mídia não pode passar de {self.status.value} para {status.value}."
            )
        self.status = status
        # Só a falha carrega mensagem; os demais estados não levam erro antigo.
        self.error_message = error_message if status == MediaStatus.FAILED else None
        self.updated_at = utcnow()

    def mark_as_processing(self) -> None:
        """Transcrição ou extração do texto começou."""
        self._change_to(MediaStatus.PROCESSING)

    def mark_text_ready(self) -> None:
        """Texto pronto: a análise começa."""
        self._change_to(MediaStatus.ANALYZING)

    def mark_as_completed(self) -> None:
        """Análise concluída."""
        self._change_to(MediaStatus.COMPLETED)

    def mark_as_failed(self, error_message: str) -> None:
        self._change_to(MediaStatus.FAILED, error_message or "Erro desconhecido")

    @property
    def file_size(self) -> int:
        return self.file_size_bytes

    def can_be_reprocessed(self) -> bool:
        """Só uma mídia que falhou pode ser processada de novo.

        Reprocessar apaga a transcrição e a análise anteriores: numa mídia
        concluída, perderia o resumo corrigido e as avaliações; numa mídia em
        processamento, apagaria os resultados enquanto o worker ainda grava.
        """
        return self.status == MediaStatus.FAILED

    def ensure_can_be_reprocessed(self) -> None:
        if not self.can_be_reprocessed():
            raise MediaNotReprocessableError(
                "Só é possível reprocessar uma mídia cujo processamento falhou "
                f"(estado atual: {self.status.value})."
            )

    def process(self) -> None:
        """Reinicia o processamento de uma mídia que falhou."""
        self.ensure_can_be_reprocessed()
        self.mark_as_processing()

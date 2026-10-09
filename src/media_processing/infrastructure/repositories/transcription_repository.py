"""Repositório das transcrições (SQLAlchemy, sessão assíncrona)."""
import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select

from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.infrastructure.persistence.models import TranscriptionModel
from src.shared.infrastructure.database.unit_of_work import commit as uow_commit


class TranscriptionRepository:
    """SQLAlchemy implementation of the transcription repository."""

    def __init__(self, db):
        self.db = db

    async def save(self, transcription: Transcription) -> Transcription:
        """Insere ou atualiza numa só ida ao banco (merge pela chave primária).

        Antes: uma consulta para saber se existia, depois add ou merge, e um
        refresh após o commit.
        """
        await self.db.merge(TranscriptionModel.from_domain(transcription))
        await uow_commit(self.db)
        return transcription

    async def get_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        result = await self.db.execute(
            select(TranscriptionModel).where(TranscriptionModel.id == transcription_id)
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def get_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        result = await self.db.execute(
            select(TranscriptionModel).where(TranscriptionModel.media_id == media_id)
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_unfinished(self, started_before: datetime.datetime) -> List[Transcription]:
        """Transcrições na fila ou em processamento desde antes de started_before
        (candidatas a paradas; a política decide quais passaram do prazo)."""
        started = func.coalesce(TranscriptionModel.updated_at, TranscriptionModel.created_at)
        stmt = select(TranscriptionModel).where(
            TranscriptionModel.status.in_(
                [TranscriptionStatus.PENDING, TranscriptionStatus.PROCESSING]
            ),
            started < started_before,
        )
        result = await self.db.execute(stmt)
        return [model.to_domain() for model in result.scalars().all()]

    async def media_ids_with_records(self, media_ids: List[UUID]) -> set:
        if not media_ids:
            return set()
        stmt = select(TranscriptionModel.media_id).where(TranscriptionModel.media_id.in_(media_ids))
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    async def media_ids_finished_before(self, media_ids: List[UUID], finished_before: datetime.datetime) -> set:
        """Mídias com transcrição concluída ou com falha, encerrada antes do instante dado."""
        if not media_ids:
            return set()
        stmt = select(TranscriptionModel.media_id).where(
            TranscriptionModel.media_id.in_(media_ids),
            TranscriptionModel.status.in_([TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED]),
            func.coalesce(TranscriptionModel.updated_at, TranscriptionModel.created_at) < finished_before,
        )
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    async def segment_correction_counts(self) -> tuple[int, int, int, int]:
        """Transcrições concluídas, quantas tiveram trecho corrigido, trechos no
        total e trechos corrigidos (o original fica em ``original_text``)."""
        stmt = select(TranscriptionModel.segments).where(TranscriptionModel.status == TranscriptionStatus.COMPLETED)
        transcriptions = corrected_transcriptions = segments_total = segments_corrected = 0
        for (segments,) in (await self.db.execute(stmt)).all():
            items = [s for s in (segments or []) if isinstance(s, dict)]
            corrected = sum(1 for s in items if "original_text" in s)
            transcriptions += 1
            corrected_transcriptions += corrected > 0
            segments_total += len(items)
            segments_corrected += corrected
        return transcriptions, corrected_transcriptions, segments_total, segments_corrected

    async def delete_by_media_id(self, media_id: UUID) -> None:
        result = await self.db.execute(
            select(TranscriptionModel).where(TranscriptionModel.media_id == media_id)
        )
        for entity in result.scalars().all():
            await self.db.delete(entity)
        await uow_commit(self.db)

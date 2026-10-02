"""Repositório das transcrições (SQLAlchemy, sessão assíncrona)."""
import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select

from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.infrastructure.persistence.models import TranscriptionModel
from src.shared.infrastructure.database.unit_of_work import commit as uow_commit
from src.shared.infrastructure.database.unit_of_work import rollback as uow_rollback


class TranscriptionRepository:
    """SQLAlchemy implementation of the transcription repository."""

    def __init__(self, db):
        self.db = db

    async def save(self, transcription: Transcription) -> Transcription:
        """Upsert simplificado que cumpre o port TranscriptionRepositoryPort."""
        existing = await self.get_by_id(transcription.id)
        if existing is None:
            await self.add(transcription)
        else:
            await self.update(transcription)
        return transcription

    async def get_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        await uow_rollback(self.db)  # garante conexão livre
        result = await self.db.execute(
            select(TranscriptionModel).where(TranscriptionModel.id == transcription_id)
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def add(self, transcription: Transcription) -> None:
        model = TranscriptionModel.from_domain(transcription)
        self.db.add(model)
        await uow_commit(self.db)
        await self.db.refresh(model)
        transcription.id = model.id

    async def update(self, transcription: Transcription) -> None:
        await self.db.merge(TranscriptionModel.from_domain(transcription))
        await uow_commit(self.db)

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

    async def delete_by_media_id(self, media_id: UUID) -> None:
        await uow_rollback(self.db)  # garante conexão livre
        result = await self.db.execute(
            select(TranscriptionModel).where(TranscriptionModel.media_id == media_id)
        )
        for entity in result.scalars().all():
            await self.db.delete(entity)
        await uow_commit(self.db)

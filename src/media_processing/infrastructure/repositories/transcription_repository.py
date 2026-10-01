# src/transcription/infrastructure/transcription_repository.py
import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select

from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.infrastructure.persistence.models import TranscriptionModel
from src.shared.infrastructure.database.db import is_async_session
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
        if is_async_session(self.db):
            await uow_rollback(self.db)  # garante conexão livre
            result = await self.db.execute(
                select(TranscriptionModel).where(
                    TranscriptionModel.id == transcription_id
                )
            )
            model = result.scalar_one_or_none()
            return model.to_domain() if model else None
        else:  # It's a sync session
            return self.get_by_id_sync(transcription_id)

    def get_by_id_sync(self, transcription_id: UUID) -> Optional[Transcription]:
        stmt = select(TranscriptionModel).where(
            TranscriptionModel.id == transcription_id
        )
        result = self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def add(self, transcription: Transcription) -> None:
        model = TranscriptionModel.from_domain(transcription)
        if is_async_session(self.db):
            self.db.add(model)
            await uow_commit(self.db) # Flush + Commit
            await self.db.refresh(model)
            transcription.id = model.id
        else:  # It's a sync session
            self.add_sync(transcription)

    def add_sync(self, transcription: Transcription) -> Transcription:
        model = TranscriptionModel.from_domain(transcription)
        self.db.add(model)
        self.db.commit() # Flush + Commit
        self.db.refresh(model)
        transcription.id = model.id
        return transcription

    async def update(self, transcription: Transcription) -> None:
        model = TranscriptionModel.from_domain(transcription)
        if is_async_session(self.db):
            await self.db.merge(model)
            await uow_commit(self.db) # Flush + Commit
        else:  # It's a sync session
            self.update_sync(transcription)

    def update_sync(self, transcription: Transcription) -> Transcription:
        model = TranscriptionModel.from_domain(transcription)
        self.db.merge(model)
        self.db.commit() # Flush + Commit
        return transcription

    async def get_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        if is_async_session(self.db):
            result = await self.db.execute(
                select(TranscriptionModel).where(
                    TranscriptionModel.media_id == media_id
                )
            )
            model = result.scalar_one_or_none()
            return model.to_domain() if model else None
        else:  # It's a sync session
            return self.get_by_media_id_sync(media_id)

    def get_by_media_id_sync(self, media_id: UUID) -> Optional[Transcription]:
        stmt = select(TranscriptionModel).where(
            TranscriptionModel.media_id == media_id
        )
        result = self.db.execute(stmt)
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
        if is_async_session(self.db):
            await uow_rollback(self.db)  # garante conexão livre
            stmt = select(TranscriptionModel).where(
                TranscriptionModel.media_id == media_id
            )
            result = await self.db.execute(stmt)
            for entity in result.scalars().all():
                await self.db.delete(entity)
            await uow_commit(self.db)
        else:
            self.delete_by_media_id_sync(media_id)

    def delete_by_media_id_sync(self, media_id: UUID) -> None:
        stmt = select(TranscriptionModel).where(TranscriptionModel.media_id == media_id)
        result = self.db.execute(stmt)
        for entity in result.scalars().all():
            self.db.delete(entity)
        self.db.commit()

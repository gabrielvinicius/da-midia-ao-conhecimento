"""Consulta as mídias sem registro de processamento (PostgreSQL)."""
from __future__ import annotations

import datetime
from typing import List

from sqlalchemy import String, and_, cast, column, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_processing.application.ports import UnstartedMedia
from src.media_processing.infrastructure.persistence.models import TranscriptionModel
from src.shared.domain.events import MediaUploaded

# Referência leve à tabela "media", sem importar o modelo de outro módulo.
_media = table(
    "media",
    column("id"),
    column("user_id"),
    column("filename"),
    column("media_type"),
    column("status"),
    column("storage_provider"),
    column("original_file_path"),
    column("file_size"),
    column("language"),
    column("transcription_provider"),
    column("summarization_provider"),
    column("sentiment_provider"),
    column("topic_modeling_provider"),
    column("created_at"),
)

# Estados em que a mídia ainda espera pelo processamento (nomes do enum).
_WAITING = ("UPLOADED", "PROCESSING")


class SqlUnstartedMediaQuery:
    def __init__(self, session: AsyncSession, limit: int = 50) -> None:
        self._session = session
        self._limit = limit

    async def list_unstarted(
        self, uploaded_before: datetime.datetime
    ) -> List[UnstartedMedia]:
        cutoff = uploaded_before.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        stmt = (
            select(_media)
            .outerjoin(
                TranscriptionModel.__table__,
                TranscriptionModel.__table__.c.media_id == _media.c.id,
            )
            .where(
                and_(
                    TranscriptionModel.__table__.c.id.is_(None),
                    cast(_media.c.status, String).in_(_WAITING),
                    _media.c.created_at < cutoff,
                )
            )
            .order_by(_media.c.created_at)
            .limit(self._limit)
        )
        rows = (await self._session.execute(stmt)).mappings().all()
        return [self._to_unstarted(row) for row in rows]

    @staticmethod
    def _to_unstarted(row) -> UnstartedMedia:
        media_type = row["media_type"]
        media_type = getattr(media_type, "value", media_type)
        return UnstartedMedia(
            upload=MediaUploaded(
                media_id=str(row["id"]),
                user_id=str(row["user_id"]) if row["user_id"] else None,
                filename=row["filename"],
                media_type=str(media_type).lower() if media_type else None,
                storage_provider=row["storage_provider"],
                file_path=row["original_file_path"],
                file_size_bytes=row["file_size"],
                language=row["language"],
                transcription_provider=row["transcription_provider"],
                summarization_provider=row["summarization_provider"],
                sentiment_provider=row["sentiment_provider"],
                topic_modeling_provider=row["topic_modeling_provider"],
                correlation_id=f"recovered-{row['id']}",
            ),
            uploaded_at=row["created_at"],
        )

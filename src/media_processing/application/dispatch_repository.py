"""Lookup helpers for media dispatch workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.shared.infrastructure.database import get_sync_session


@dataclass(slots=True)
class DispatchRecord:
    media_id: UUID
    file_path: str
    storage_provider: str
    transcription_provider: str
    language: str
    media_type: Optional[str]
    file_size_bytes: Optional[int]
    summarization_provider: Optional[str]
    sentiment_provider: Optional[str]
    topic_modeling_provider: Optional[str]


class MediaDispatchRepository:
    """Provides read/write helpers for media entities before processing."""

    def mark_processing(self, media_id: UUID) -> Optional[DispatchRecord]:
        from src.media_management.domain.enums import MediaStatus
        from src.media_management.infrastructure.orm.media_entity import MediaEntity

        with get_sync_session() as session:
            media: MediaEntity | None = session.get(MediaEntity, media_id)
            if media is None:
                return None

            media.status = MediaStatus.PROCESSING
            media.error_message = None
            session.flush()

            media_type_value = getattr(media, "media_type", None)
            if media_type_value is not None:
                media_type_value = getattr(media_type_value, "value", str(media_type_value))

            return DispatchRecord(
                media_id=media_id,
                file_path=media.original_file_path or "",
                storage_provider=media.storage_provider or "local",
                transcription_provider=media.transcription_provider or "fastwhisper",
                language=media.language or "en",
                media_type=media_type_value,
                file_size_bytes=getattr(media, "file_size", None),
                summarization_provider=getattr(media, "summarization_provider", None),
                sentiment_provider=getattr(media, "sentiment_provider", None),
                topic_modeling_provider=getattr(media, "topic_modeling_provider", None),
            )

    def mark_failed(self, media_id: UUID, reason: str) -> None:
        from src.media_management.domain.enums import MediaStatus
        from src.media_management.infrastructure.orm.media_entity import MediaEntity

        truncated = reason[:250]
        with get_sync_session() as session:
            media: MediaEntity | None = session.get(MediaEntity, media_id)
            if media is None:
                return
            media.status = MediaStatus.FAILED
            media.error_message = truncated
            session.flush()


__all__ = ["DispatchRecord", "MediaDispatchRepository"]

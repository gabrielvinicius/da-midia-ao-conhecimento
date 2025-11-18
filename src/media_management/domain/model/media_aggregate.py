"""Immutable aggregate representing a media resource."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Optional, Union
from uuid import UUID, uuid4

from src.media_management.domain.enums import MediaStatus, MediaType

UUIDLike = Union[UUID, str]
_MISSING = object()


def _coerce_uuid(value: UUIDLike) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _ensure_timezone(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class MediaAggregate:
    """Pure domain representation of a stored media item."""

    id: UUID
    user_id: UUID
    original_file_path: str
    media_type: MediaType
    storage_provider: str = "local"
    status: MediaStatus = MediaStatus.UPLOADED
    transcription_provider: Optional[str] = None
    summarization_provider: Optional[str] = None
    sentiment_provider: Optional[str] = None
    topic_modeling_provider: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    language: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    duration: Optional[int] = None

    def __post_init__(self) -> None:  # pragma: no cover - defensive normalization
        object.__setattr__(self, "id", _coerce_uuid(self.id))
        object.__setattr__(self, "user_id", _coerce_uuid(self.user_id))

        media_type = self.media_type
        if not isinstance(media_type, MediaType):
            object.__setattr__(self, "media_type", MediaType(str(media_type)))

        status = self.status
        if not isinstance(status, MediaStatus):
            object.__setattr__(self, "status", MediaStatus(str(status)))

        created_at = self.created_at or datetime.now(timezone.utc)
        object.__setattr__(self, "created_at", _ensure_timezone(created_at))

    @classmethod
    def create(
        cls,
        *,
        user_id: UUIDLike,
        original_file_path: str,
        media_type: MediaType | str,
        storage_provider: str,
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
        language: Optional[str] = None,
        filename: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        duration: Optional[int] = None,
        created_at: Optional[datetime] = None,
        status: MediaStatus | str = MediaStatus.UPLOADED,
        media_id: Optional[UUIDLike] = None,
    ) -> "MediaAggregate":
        """Factory helper that normalises defaults for new media."""
        return cls(
            id=_coerce_uuid(media_id) if media_id else uuid4(),
            user_id=_coerce_uuid(user_id),
            original_file_path=original_file_path,
            media_type=MediaType(str(media_type)) if not isinstance(media_type, MediaType) else media_type,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider,
            sentiment_provider=sentiment_provider,
            topic_modeling_provider=topic_modeling_provider,
            language=language,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            duration=duration,
            created_at=created_at or datetime.now(timezone.utc),
            status=MediaStatus(str(status)) if not isinstance(status, MediaStatus) else status,
        )

    # ------------------------------------------------------------------
    # Business behaviour
    # ------------------------------------------------------------------
    def mark_processing(self) -> "MediaAggregate":
        return self.with_status(MediaStatus.PROCESSING)

    def mark_completed(self) -> "MediaAggregate":
        return self.with_status(MediaStatus.COMPLETED, error_message=None)

    def mark_failed(self, reason: str) -> "MediaAggregate":
        return self.with_status(MediaStatus.FAILED, error_message=reason)

    def clear_error(self) -> "MediaAggregate":
        return self.update(error_message=None)

    def with_status(
        self,
        status: MediaStatus | str,
        *,
        error_message: Optional[str] = None,
    ) -> "MediaAggregate":
        new_status = status if isinstance(status, MediaStatus) else MediaStatus(str(status))
        return replace(self, status=new_status, error_message=error_message)

    def update(
        self,
        *,
        original_file_path: Optional[str] = None,
        filename: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        duration: Optional[int] = None,
        language: Optional[str] = None,
        created_at: Optional[datetime] = None,
        error_message: object = _MISSING,
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
    ) -> "MediaAggregate":
        """Return a copy with the provided fields replaced."""
        updates: dict[str, object] = {}
        if original_file_path is not None:
            updates["original_file_path"] = original_file_path
        if filename is not None:
            updates["filename"] = filename
        if file_size is not None:
            updates["file_size"] = file_size
        if mime_type is not None:
            updates["mime_type"] = mime_type
        if duration is not None:
            updates["duration"] = duration
        if language is not None:
            updates["language"] = language
        if created_at is not None:
            updates["created_at"] = _ensure_timezone(created_at)
        if error_message is not _MISSING:
            updates["error_message"] = error_message
        if transcription_provider is not None:
            updates["transcription_provider"] = transcription_provider
        if summarization_provider is not None:
            updates["summarization_provider"] = summarization_provider
        if sentiment_provider is not None:
            updates["sentiment_provider"] = sentiment_provider
        if topic_modeling_provider is not None:
            updates["topic_modeling_provider"] = topic_modeling_provider

        if not updates:
            return self
        return replace(self, **updates)

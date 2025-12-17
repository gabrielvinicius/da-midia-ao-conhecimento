from __future__ import annotations

import datetime
from typing import Optional
from uuid import UUID

from src.shared.domain.base_entity import BaseEntity
from src.shared.domain.enums import MediaStatus, MediaType


class Media(BaseEntity):
    """Media aggregate root."""

    user_id: UUID
    filename: str
    file_size_bytes: int
    media_type: MediaType
    storage_provider: str
    original_file_path: str
    status: MediaStatus
    transcription_provider: Optional[str]
    summarization_provider: Optional[str]
    sentiment_provider: Optional[str]
    topic_modeling_provider: Optional[str]
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
        media_type: MediaType,
        storage_provider: str,
        original_file_path: str,
        status: MediaStatus = MediaStatus.UPLOADED,
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
        language: str = "auto",
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        error_message: Optional[str] = None,
    ):
        super().__init__(media_id)
        self.user_id = user_id
        self.filename = filename
        self.file_size_bytes = file_size_bytes
        self.media_type = media_type
        self.storage_provider = storage_provider
        self.original_file_path = original_file_path
        self.status = status
        self.transcription_provider = transcription_provider
        self.summarization_provider = summarization_provider
        self.sentiment_provider = sentiment_provider
        self.topic_modeling_provider = topic_modeling_provider
        self.language = language
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = updated_at or datetime.datetime.now(datetime.timezone.utc)
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
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
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
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider,
            sentiment_provider=sentiment_provider,
            topic_modeling_provider=topic_modeling_provider,
            language=language,
        )

    def mark_as_processing(self) -> None:
        self.status = MediaStatus.PROCESSING
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def mark_as_completed(self) -> None:
        self.status = MediaStatus.COMPLETED
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def mark_as_failed(self, error_message: str) -> None:
        self.status = MediaStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def update(
        self,
        filename: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        created_at: Optional[datetime.datetime] = None,
    ) -> Media:
        if filename:
            self.filename = filename
        if file_size is not None:
            self.file_size_bytes = file_size
        if created_at:
            self.created_at = created_at
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
        return self

    @property
    def file_size(self) -> int:
        return self.file_size_bytes

    def process(self) -> None:
        """Trigger processing state transition."""
        if self.status == MediaStatus.FAILED:
             self.error_message = None
        self.mark_as_processing()

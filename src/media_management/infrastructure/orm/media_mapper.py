"""Mapping utilities between aggregates and ORM entities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.media_management.domain.model import MediaAggregate

from .media_entity import MediaEntity


def _to_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


class MediaMapper:
    """Converts between :class:`MediaAggregate` and :class:`MediaEntity`."""

    def to_domain(
        self,
        entity: MediaEntity,
        *,
        template: Optional[MediaAggregate] = None,
    ) -> MediaAggregate:
        aggregate = MediaAggregate(
            id=entity.id,
            user_id=entity.user_id,
            original_file_path=entity.original_file_path,
            media_type=entity.media_type,
            storage_provider=entity.storage_provider,
            transcription_provider=entity.transcription_provider,
            summarization_provider=entity.summarization_provider,
            status=entity.status,
            created_at=entity.created_at,
            error_message=entity.error_message,
            language=entity.language,
        )

        if template is not None:
            aggregate = aggregate.update(
                filename=template.filename,
                file_size=template.file_size,
                mime_type=template.mime_type,
                duration=template.duration,
            )

        return aggregate

    def to_entity(self, aggregate: MediaAggregate) -> MediaEntity:
        entity = MediaEntity(
            id=aggregate.id,
            user_id=aggregate.user_id,
            original_file_path=aggregate.original_file_path,
            media_type=aggregate.media_type,
            storage_provider=aggregate.storage_provider,
            transcription_provider=aggregate.transcription_provider,
            summarization_provider=aggregate.summarization_provider,
            status=aggregate.status,
            created_at=_to_naive(aggregate.created_at) or datetime.utcnow(),
            error_message=aggregate.error_message,
            language=aggregate.language,
        )
        return entity

    def apply_to_entity(self, entity: MediaEntity, aggregate: MediaAggregate) -> MediaEntity:
        entity.user_id = aggregate.user_id
        entity.original_file_path = aggregate.original_file_path
        entity.media_type = aggregate.media_type
        entity.storage_provider = aggregate.storage_provider
        entity.transcription_provider = aggregate.transcription_provider
        entity.summarization_provider = aggregate.summarization_provider
        entity.status = aggregate.status
        entity.error_message = aggregate.error_message
        entity.language = aggregate.language
        entity.created_at = _to_naive(aggregate.created_at) or entity.created_at
        return entity

    def merge_transient_data(
        self,
        persisted: MediaAggregate,
        template: Optional[MediaAggregate],
    ) -> MediaAggregate:
        if template is None:
            return persisted
        return persisted.update(
            filename=template.filename,
            file_size=template.file_size,
            mime_type=template.mime_type,
            duration=template.duration,
        )

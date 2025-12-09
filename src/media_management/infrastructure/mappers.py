"""Mappers for converting between Media Entities and Aggregates."""

from src.media_management.domain.model import MediaAggregate
from src.media_management.infrastructure.persistence.models import MediaEntity


class MediaMapper:
    """Maps MediaEntity <-> MediaAggregate."""

    def to_domain(self, entity: MediaEntity) -> MediaAggregate:
        return MediaAggregate(
            id=entity.id,
            user_id=entity.user_id,
            original_file_path=entity.original_file_path,
            media_type=entity.media_type,
            storage_provider=entity.storage_provider,
            status=entity.status,
            transcription_provider=entity.transcription_provider,
            summarization_provider=entity.summarization_provider,
            sentiment_provider=entity.sentiment_provider,
            topic_modeling_provider=entity.topic_modeling_provider,
            created_at=entity.created_at,
            error_message=entity.error_message,
            language=entity.language,
            filename=entity.filename,
            file_size=entity.file_size,
            mime_type=entity.mime_type,
            duration=entity.duration,
        )

    def to_entity(self, aggregate: MediaAggregate) -> MediaEntity:
        return MediaEntity(
            id=aggregate.id,
            user_id=aggregate.user_id,
            original_file_path=aggregate.original_file_path,
            media_type=aggregate.media_type,
            storage_provider=aggregate.storage_provider,
            status=aggregate.status,
            created_at=aggregate.created_at,
            error_message=aggregate.error_message,
            transcription_provider=aggregate.transcription_provider,
            summarization_provider=aggregate.summarization_provider,
            sentiment_provider=aggregate.sentiment_provider,
            topic_modeling_provider=aggregate.topic_modeling_provider,
            language=aggregate.language,
            filename=aggregate.filename,
            file_size=aggregate.file_size,
            mime_type=aggregate.mime_type,
            duration=aggregate.duration,
        )

    def merge_transient_data(self, persistent: MediaAggregate, transient: MediaAggregate) -> MediaAggregate:
        """Merges persistent state with potentially newer transient state."""
        # Currently just returns persistent, but can be extended if we have transient-only fields
        return persistent

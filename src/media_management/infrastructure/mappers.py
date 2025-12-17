"""Mappers for converting between Media Entities and domain Media."""

from src.media_management.domain import Media
from src.media_management.infrastructure.persistence.models import MediaEntity
from src.shared.domain.enums import MediaStatus, MediaType


class MediaMapper:
    """Maps MediaEntity <-> Media."""

    def to_domain(self, entity: MediaEntity) -> Media:
        return Media(
            media_id=entity.id,
            user_id=entity.user_id,
            filename=entity.filename or "",
            file_size_bytes=entity.file_size or 0,
            media_type=entity.media_type or MediaType.TEXT,
            storage_provider=entity.storage_provider,
            original_file_path=entity.original_file_path,
            status=entity.status or MediaStatus.UPLOADED,
            transcription_provider=entity.transcription_provider,
            summarization_provider=entity.summarization_provider,
            sentiment_provider=entity.sentiment_provider,
            topic_modeling_provider=entity.topic_modeling_provider,
            language=entity.language or "auto",
            created_at=entity.created_at,
            updated_at=entity.created_at,
            error_message=entity.error_message,
        )

    def to_entity(self, media: Media) -> MediaEntity:
        return MediaEntity(
            id=media.id,
            user_id=media.user_id,
            original_file_path=media.original_file_path,
            media_type=media.media_type,
            storage_provider=media.storage_provider,
            status=media.status,
            created_at=media.created_at,
            error_message=media.error_message,
            transcription_provider=media.transcription_provider,
            summarization_provider=media.summarization_provider,
            sentiment_provider=media.sentiment_provider,
            topic_modeling_provider=media.topic_modeling_provider,
            language=media.language,
            filename=media.filename,
            file_size=media.file_size_bytes,
            mime_type=None,
            duration=None,
        )

    def merge_transient_data(self, persistent: Media, transient: Media) -> Media:
        """Merges persistent state with potentially newer transient state."""
        # Currently just returns persistent; extend if transient-only fields appear.
        return persistent

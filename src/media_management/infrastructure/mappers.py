"""Mappers for converting between Media Entities and domain Media."""

from src.media_management.domain import Media
from src.media_management.infrastructure.persistence.models import MediaEntity
from src.media_management.domain.enums import MediaStatus, MediaType
import datetime


class MediaMapper:
    """Maps MediaEntity <-> Media."""

    @staticmethod
    def _naive(dt: datetime.datetime | None) -> datetime.datetime | None:
        if dt is None:
            return None
        if dt.tzinfo:
            return dt.replace(tzinfo=None)
        return dt

    def to_domain(self, entity: MediaEntity) -> Media:
        return Media(
            media_id=entity.id,
            user_id=entity.user_id,
            filename=entity.filename or "",
            file_size_bytes=entity.file_size or 0,
            mime_type=entity.mime_type,
            duration=entity.duration,
            media_type=entity.media_type or MediaType.TEXT,
            storage_provider=entity.storage_provider,
            original_file_path=entity.original_file_path,
            status=entity.status or MediaStatus.UPLOADED,
            transcription_provider=entity.transcription_provider,
            language=entity.language or "auto",
            created_at=entity.created_at,
            updated_at=(entity.updated_at or entity.created_at),
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
            created_at=self._naive(media.created_at),
            updated_at=self._naive(media.updated_at),
            error_message=media.error_message,
            transcription_provider=media.transcription_provider,
            language=media.language,
            filename=media.filename,
            file_size=media.file_size_bytes,
            mime_type=media.mime_type,
            duration=media.duration,
        )

    def merge_transient_data(self, persistent: Media, transient: Media) -> Media:
        """Merges persistent state with potentially newer transient state."""
        # Currently just returns persistent; extend if transient-only fields appear.
        return persistent

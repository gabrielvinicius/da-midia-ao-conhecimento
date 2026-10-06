"""Como uma mídia já registrada é anunciada ao processamento."""
from __future__ import annotations

from typing import Optional

from src.media_management.domain import Media
from src.shared.domain.events import MediaUploaded


def upload_event_for(media: Media, *, correlation_id: Optional[str] = None) -> MediaUploaded:
    """MediaUploaded a partir do registro da mídia (reprocessamento e recuperação)."""
    media_type = getattr(media.media_type, "value", media.media_type)
    return MediaUploaded(
        media_id=str(media.id),
        user_id=str(media.user_id),
        filename=media.filename,
        storage_provider=media.storage_provider,
        media_type=str(media_type).lower() if media_type else None,
        file_size_bytes=media.file_size,
        transcription_provider=media.transcription_provider,
        language=media.language,
        correlation_id=correlation_id,
        file_path=media.original_file_path,
    )

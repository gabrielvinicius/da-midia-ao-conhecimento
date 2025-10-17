# src/media_management/application/services/media_factory.py
from uuid import UUID
from src.media_management.domain.media import Media, MediaType, MediaStatus


class MediaFactory:
    @staticmethod
    def create(
        media_id: UUID,
        user_id: UUID,
        file_path: str,
        media_type: MediaType,
        storage_provider: str,
        transcription_provider: str,
        summarization_provider: str,
    ) -> Media:
        return Media(
            id=media_id,
            user_id=user_id,
            original_file_path=file_path,
            media_type=media_type,
            status=MediaStatus.UPLOADED,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider,
        )

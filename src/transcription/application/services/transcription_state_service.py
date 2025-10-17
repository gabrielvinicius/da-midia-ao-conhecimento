# src/transcription/application/services/transcription_state_service.py
from src.media_management.domain.media import Media
from src.media_management.infrastructure.media_repository import MediaRepository
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository


class TranscriptionStateService:
    """Manages the state of Media and Transcription entities during the transcription process."""

    def __init__(
        self,
        media_repository: MediaRepository,
        transcription_repository: TranscriptionRepository,
    ):
        self.media_repository = media_repository
        self.transcription_repository = transcription_repository

    async def start_processing(self, media: Media, language: str, provider: str) -> Transcription:
        """Marks the media and transcription as processing."""
        media.language = language
        media.process()
        await self.media_repository.save(media)

        transcription = Transcription(
            media_id=media.id,
            status=TranscriptionStatus.PROCESSING,
            provider=provider
        )
        await self.transcription_repository.save(transcription)
        return transcription

    async def complete_processing(self, media: Media, transcription: Transcription, text: str):
        """Marks the media and transcription as completed."""
        transcription.mark_as_completed(text)
        await self.transcription_repository.save(transcription)

        media.complete()
        await self.media_repository.save(media)

    async def fail_processing(self, media: Media, error: str):
        """Marks the media as failed."""
        media.fail(error[:500])  # Truncate error to fit model
        await self.media_repository.save(media)

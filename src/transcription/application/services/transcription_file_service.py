# src/transcription/application/services/transcription_file_service.py
from src.storage.application.storage_service import StorageService


class TranscriptionFileService:
    """Handles file operations related to the transcription process."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service

    async def download_audio(self, file_path: str) -> bytes:
        """Downloads the audio file from the storage service."""
        audio_bytes, _ = await self.storage_service.download(file_path)
        return audio_bytes

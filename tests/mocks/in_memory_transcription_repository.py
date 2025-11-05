# tests/mocks/in_memory_transcription_repository.py
from typing import Dict, Optional

from src.media_processing.transcription.domain.transcription import Transcription


class InMemoryTranscriptionRepository:
    def __init__(self):
        self.transcriptions: Dict[str, Transcription] = {}

    async def save(self, transcription: Transcription) -> Transcription:
        self.transcriptions[str(transcription.id)] = transcription
        return transcription

    async def find_by_id(self, transcription_id: str) -> Optional[Transcription]:
        return self.transcriptions.get(str(transcription_id))

    async def find_by_media_id(self, media_id: str) -> Optional[Transcription]:
        for trans in self.transcriptions.values():
            if str(trans.media_id) == str(media_id):
                return trans
        return None

    def clear(self):
        self.transcriptions.clear()

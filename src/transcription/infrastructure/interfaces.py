# src/transcription/infrastructure/interfaces.py
from abc import ABC, abstractmethod
from typing import Optional


class ISpeechRecognition(ABC):

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the name of the speech recognition provider."""
        pass

    @abstractmethod
    async def transcribe(self, file: bytes, language: str = "en") -> Optional[str]:
        """Transcribes an audio file to text, returning a simple string."""
        pass

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class ISpeechRecognition(ABC):

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the name of the speech recognition provider."""
        pass

    @abstractmethod
    async def transcribe(self, file: bytes, language: str = "en") -> Optional[Dict[str, Any]]:
        """Transcribes an audio file to text, returning a structured result with timestamps."""
        pass

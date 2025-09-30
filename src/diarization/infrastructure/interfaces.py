# src/diarization/infrastructure/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IDiarizationService(ABC):
    """Abstract interface for a speaker diarization service."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the name of the diarization provider."""
        pass

    @abstractmethod
    def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        """Performs speaker diarization on the given audio file."""
        pass

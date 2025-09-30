# src/diarization/infrastructure/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IDiarizationService(ABC):
    """Interface for a speaker diarization service."""

    @abstractmethod
    def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        """Analyzes an audio file and returns a list of speaker segments.

        Args:
            audio_path: The local path to the audio file to be analyzed.

        Returns:
            A list of dictionaries, where each dictionary represents a speaker segment
            and contains keys like 'speaker', 'start', and 'end'.
        """
        pass

"""Command definition for triggering sentiment analysis."""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class AnalyzeSentimentCommand:
    """Encapsulates the information required to run sentiment analysis."""

    transcription_id: str
    provider: str
    model: Optional[str] = None
    language: Optional[str] = None
    schedule_only: bool = False


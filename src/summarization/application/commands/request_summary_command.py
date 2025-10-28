"""Command object for requesting a summarization operation."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class RequestSummaryCommand:
    """Encapsulates the intent of requesting a new summary generation."""

    transcription_id: str
    provider: str
    strategy: Optional[str] = None


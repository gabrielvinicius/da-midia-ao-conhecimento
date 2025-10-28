"""Command object used by the summarization pipeline."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True, slots=True)
class ProcessSummaryCommand:
    """Collects all information required to process a summary."""

    transcription_id: Optional[str] = None
    media_id: Optional[str] = None
    text_content: Optional[str] = None
    provider: str = "huggingface"
    strategy: Optional[str] = None
    max_length: Optional[int] = None
    options: Optional[Dict[str, Any]] = None


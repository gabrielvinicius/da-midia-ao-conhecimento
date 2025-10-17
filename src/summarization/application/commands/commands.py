"""
Summarization Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessSummaryCommand:
    """Command to process summary"""
    media_id: str
    text_content: str
    provider: str


@dataclass(frozen=True)
class RequestSummaryCommand:
    """Command to request summary"""
    transcription_id: str
    provider: str
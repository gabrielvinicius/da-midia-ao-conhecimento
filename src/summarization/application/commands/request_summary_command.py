# src/summarization/application/commands/request_summary_command.py
from dataclasses import dataclass

@dataclass(frozen=True)
class RequestSummaryCommand:
    """Command to request a new summary."""
    transcription_id: str
    provider: str

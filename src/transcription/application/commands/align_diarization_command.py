# src/transcription/application/commands/align_diarization_command.py
from dataclasses import dataclass
from typing import List, Dict, Any
from uuid import UUID

@dataclass(frozen=True)
class AlignDiarizationCommand:
    """Command to align diarization results with a transcription."""
    media_id: UUID
    diarization_result: List[Dict[str, Any]]

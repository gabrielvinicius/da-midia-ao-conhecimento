"""Compatibility command objects for legacy handlers.

These light-weight dataclasses mirror the old CQRS commands that used to live
under ``src.transcription`` so existing tests and integrations keep working
while the refactored services power the behaviour behind the scenes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProcessTranscriptionCommand:
    """Legacy command used to trigger transcription processing."""

    media_id: str
    file_path: str
    storage_provider: str
    transcription_provider: str
    language: str = "en"


__all__ = ["ProcessTranscriptionCommand"]

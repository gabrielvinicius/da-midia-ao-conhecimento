"""Command object mirroring the legacy video upload CQRS contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UploadVideoCommand:
    user_id: str
    file: bytes
    filename: str
    storage_provider: str


__all__ = ["UploadVideoCommand"]

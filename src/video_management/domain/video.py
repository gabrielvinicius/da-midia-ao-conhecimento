"""Lightweight video entity used by compatibility handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(slots=True)
class Video:
    id: UUID
    user_id: str
    storage_provider: str
    file_path: str
    filename: str
    status: str = "UPLOADED"
    error_message: Optional[str] = None


__all__ = ["Video"]

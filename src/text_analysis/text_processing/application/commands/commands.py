"""Compatibility command objects for legacy text processing CQRS flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ProcessTextCommand:
    """Command instructing the system to extract and process textual content."""

    media_id: str
    file_path: str
    storage_provider: str
    language: Optional[str] = None


__all__ = ["ProcessTextCommand"]

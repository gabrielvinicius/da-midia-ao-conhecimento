from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Document:
    """Texto analisado (transcrição ou texto extraído) e seus segmentos com horário."""

    id: UUID
    text: str
    segments: Optional[list] = None

    @classmethod
    def from_payload(cls, text: str, segments: Optional[list] = None) -> "Document":
        return cls(id=uuid4(), text=text or "", segments=segments or [])


__all__ = ["Document"]

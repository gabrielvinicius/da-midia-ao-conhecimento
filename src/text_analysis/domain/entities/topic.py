from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Topic:
    id: int
    keywords: list[str]
    summary: Optional[str] = None
    summary_md: Optional[str] = None
    diagnostics: Optional[dict] = None
    snippets: list[str] | None = None
    size: int = 0
    title: Optional[str] = None
    #: Posições (em analysis.chunks) dos trechos do tema: dão o peso do tema
    #: e onde ele aparece na gravação.
    chunk_indices: list[int] = field(default_factory=list)


__all__ = ["Topic"]

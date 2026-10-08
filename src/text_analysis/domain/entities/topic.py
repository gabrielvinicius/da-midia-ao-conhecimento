from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Topic:
    id: int
    keywords: list[str]
    snippets: list[str] | None = None
    size: int = 0
    title: Optional[str] = None
    #: Posições (em analysis.chunks) dos trechos do tema: dão o peso do tema
    #: e onde ele aparece na gravação.
    chunk_indices: list[int] = field(default_factory=list)
    #: Título dado pela IA, guardado na primeira correção do usuário.
    original_title: Optional[str] = None

    def rename(self, title: str) -> None:
        if self.original_title is None:
            self.original_title = self.title or ""
        self.title = title


__all__ = ["Topic"]

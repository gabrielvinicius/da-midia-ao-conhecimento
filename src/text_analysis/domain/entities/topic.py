from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Topic:
    id: int
    keywords: List[str]
    summary: Optional[str] = None
    diagnostics: Optional[dict] = None
    snippets: List[str] | None = None
    size: int = 0
    title: Optional[str] = None


__all__ = ["Topic"]

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Topic:
    id: int
    keywords: list[str]
    summary: Optional[str] = None
    diagnostics: Optional[dict] = None
    snippets: list[str] | None = None
    size: int = 0
    title: Optional[str] = None


__all__ = ["Topic"]

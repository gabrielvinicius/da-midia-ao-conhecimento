from __future__ import annotations

from src.shared.domain.errors import DomainError as SharedDomainError


class DomainError(SharedDomainError):
    """Base domain error for text_analysis, reusing shared domain error hierarchy."""


__all__ = ["DomainError"]

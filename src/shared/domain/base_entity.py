"""Shared SQLAlchemy base entity definition."""
from __future__ import annotations

from src.shared.infrastructure.database import Base


class BaseEntity(Base):
    """Abstract base for SQLAlchemy-mapped domain entities."""

    __abstract__ = True


__all__ = ["BaseEntity"]

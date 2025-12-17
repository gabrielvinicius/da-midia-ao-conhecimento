from __future__ import annotations

import abc
from uuid import UUID


class BaseEntity(abc.ABC):
    """Base class for all domain entities."""

    def __init__(self, id: UUID) -> None:
        self.id = id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

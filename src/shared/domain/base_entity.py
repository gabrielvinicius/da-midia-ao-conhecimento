"""Base classes for Domain Driven Design entities and aggregates.

This module provides the foundational building blocks for the domain layer,
ensuring separation from infrastructure concerns (like ORM).
"""

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, TypeVar
from uuid import UUID, uuid4

T = TypeVar("T", bound="Entity")


@dataclass(kw_only=True)
class Entity(abc.ABC):
    """Abstract base class for Domain Entities.
    
    Entities are defined by their identity, not their attributes.
    """
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class AggregateRoot(Entity):
    """Abstract base class for Aggregate Roots.
    
    Aggregate Roots are the entry point for an aggregate and enforce consistency boundaries.
    They also handle domain events.
    """
    _events: List[Any] = field(default_factory=list, init=False, repr=False)

    def add_event(self, event: Any) -> None:
        """Register a domain event to be published when the transaction commits."""
        self._events.append(event)

    def clear_events(self) -> None:
        """Clear all registered domain events."""
        self._events.clear()

    @property
    def events(self) -> tuple[Any, ...]:
        """Return a read-only view of registered events."""
        return tuple(self._events)
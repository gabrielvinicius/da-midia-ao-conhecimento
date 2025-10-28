"""Domain event definitions used by the application's event bus."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base domain event with common metadata.

    The implementation keeps the structure intentionally lightweight so tests can
    instantiate simple events while production code can subclass the base class
    to add domain specific behaviour when required.
    """

    name: str = field(default_factory=lambda: "DomainEvent")
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Ensure we always expose the class name when no explicit name is
        # provided by subclasses.
        if self.name == "DomainEvent":
            object.__setattr__(self, "name", self.__class__.__name__)

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the event."""
        return {
            "event_id": str(self.event_id),
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "payload": dict(self.payload),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DomainEvent":
        """Recreate an event from persisted data."""
        return cls(
            name=str(data.get("name", cls.__name__)),
            payload=data.get("payload", {}),
            event_id=UUID(data.get("event_id")) if data.get("event_id") else uuid4(),
            occurred_at=datetime.fromisoformat(data["occurred_at"]) if data.get("occurred_at") else datetime.now(timezone.utc),
            metadata=data.get("metadata", {}),
        )


__all__ = ["DomainEvent"]

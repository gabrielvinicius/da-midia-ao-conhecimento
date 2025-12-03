"""State machine governing transitions between MediaStatus values."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from src.shared.domain.enums import MediaStatus


@dataclass(frozen=True)
class MediaStateMachine:
    """Enforces valid transitions for `MediaStatus`.

    Allowed transitions:
    - UPLOADED -> PROCESSING
    - PROCESSING -> COMPLETED | FAILED
    - FAILED -> PROCESSING (reprocess)
    - COMPLETED -> PROCESSING (manually reprocess)
    """

    transitions: Dict[MediaStatus, Iterable[MediaStatus]] = None  # type: ignore[assignment]

    def __post_init__(self):  # type: ignore[override]
        object.__setattr__(
            self,
            "transitions",
            self.transitions
            or {
                MediaStatus.UPLOADED: {MediaStatus.PROCESSING},
                MediaStatus.PROCESSING: {MediaStatus.COMPLETED, MediaStatus.FAILED},
                MediaStatus.FAILED: {MediaStatus.PROCESSING},
                MediaStatus.COMPLETED: {MediaStatus.PROCESSING},
            },
        )

    def can_transition(self, current: MediaStatus, target: MediaStatus) -> bool:
        if current == target:
            return True
        allowed = self.transitions.get(current, set())
        return target in allowed

    def assert_transition(self, current: MediaStatus, target: MediaStatus) -> None:
        if not self.can_transition(current, target):
            raise ValueError(f"Transição inválida: {current.value} -> {target.value}")


DEFAULT_MEDIA_STATE_MACHINE = MediaStateMachine()


__all__ = ["MediaStateMachine", "DEFAULT_MEDIA_STATE_MACHINE"]

"""Immutable aggregate for summarization results."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Optional, Union
from uuid import UUID, uuid4

UUIDLike = Union[UUID, str]


def _coerce_uuid(value: UUIDLike | None) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _ensure_datetime(dt: datetime | None) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SummaryStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class SummaryAggregate:
    """Pure domain representation of a summary."""

    id: UUID
    media_id: UUID
    status: SummaryStatus = SummaryStatus.PENDING
    text: Optional[str] = None
    provider: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    strategy: Optional[str] = None
    bullet_points: Optional[tuple[str, ...]] = None
    key_topics: Optional[tuple[str, ...]] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None

    def __post_init__(self) -> None:  # pragma: no cover - defensive
        object.__setattr__(self, "id", _coerce_uuid(self.id) or uuid4())
        object.__setattr__(self, "media_id", _coerce_uuid(self.media_id) or uuid4())

        status = self.status
        if not isinstance(status, SummaryStatus):
            object.__setattr__(self, "status", SummaryStatus(str(status)))

        object.__setattr__(self, "created_at", _ensure_datetime(self.created_at) or datetime.now(timezone.utc))
        object.__setattr__(self, "processed_at", _ensure_datetime(self.processed_at))
        object.__setattr__(self, "bullet_points", self._coerce_tuple(self.bullet_points))
        object.__setattr__(self, "key_topics", self._coerce_tuple(self.key_topics))

    @staticmethod
    def _coerce_tuple(values: Optional[Iterable[str]]) -> Optional[tuple[str, ...]]:
        if values is None:
            return None
        if isinstance(values, tuple):
            return values
        return tuple(values)

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        *,
        media_id: UUIDLike,
        provider: Optional[str],
        summary_id: Optional[UUIDLike] = None,
        created_at: Optional[datetime] = None,
        strategy: Optional[str] = None,
        bullet_points: Optional[Iterable[str]] = None,
        key_topics: Optional[Iterable[str]] = None,
        confidence_score: Optional[float] = None,
        processing_time: Optional[float] = None,
    ) -> "SummaryAggregate":
        return cls(
            id=_coerce_uuid(summary_id) or uuid4(),
            media_id=_coerce_uuid(media_id) or uuid4(),
            provider=provider,
            status=SummaryStatus.PROCESSING,
            created_at=created_at or datetime.now(timezone.utc),
            strategy=strategy,
            bullet_points=tuple(bullet_points) if bullet_points is not None else None,
            key_topics=tuple(key_topics) if key_topics is not None else None,
            confidence_score=confidence_score,
            processing_time=processing_time,
        )

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def mark_processing(self) -> "SummaryAggregate":
        return replace(self, status=SummaryStatus.PROCESSING, processed_at=None, error_message=None)

    def mark_as_completed(self, content: str) -> "SummaryAggregate":
        return replace(
            self,
            text=content,
            status=SummaryStatus.COMPLETED,
            processed_at=datetime.now(timezone.utc),
            error_message=None,
        )

    def mark_as_failed(self, error: str) -> "SummaryAggregate":
        return replace(
            self,
            status=SummaryStatus.FAILED,
            error_message=error,
            processed_at=datetime.now(timezone.utc),
        )

    def with_provider(self, provider: Optional[str]) -> "SummaryAggregate":
        return replace(self, provider=provider)

    def update(self, **changes: object) -> "SummaryAggregate":
        return replace(self, **changes)

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AnalysisCompleted:
    analysis_id: UUID
    media_id: Optional[UUID] = None
    transcription_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None
    topics: Optional[Any] = None
    occurred_at: datetime = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


"""Domain entity for summary results."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4


@dataclass
class Summary:
    media_id: str
    text: str
    id: str = field(default_factory=lambda: str(uuid4()))
    strategy: str = "extractive"
    provider: str = "default"
    bullet_points: List[str] = field(default_factory=list)
    key_topics: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

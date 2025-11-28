"""Domain entity for topic modeling results."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


@dataclass
class TopicModelingResult:
    media_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    topics: List[Dict[str, Any]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    num_topics: int = 0
    algorithm: str = "lda"
    coherence_score: float = 0.0
    perplexity: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

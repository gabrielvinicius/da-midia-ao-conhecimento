"""Domain entity for sentiment analysis results."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


@dataclass
class SentimentAnalysisResult:
    media_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    overall_sentiment: str = "neutral"
    sentiment_score: float = 0.0
    confidence: float = 0.0
    emotions: Dict[str, float] = field(default_factory=dict)
    sentence_sentiments: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = "default"
    model: str = "default"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

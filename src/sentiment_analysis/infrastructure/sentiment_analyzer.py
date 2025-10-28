"""Lightweight sentiment analyzer used for the default service implementation."""

from __future__ import annotations

import asyncio
import math
import re
from typing import Dict, Optional


class SimpleSentimentAnalyzer:
    """Naïve sentiment analyzer based on keyword frequency."""

    POSITIVE_WORDS = {
        "good",
        "great",
        "excellent",
        "love",
        "happy",
        "amazing",
        "wonderful",
        "recommend",
        "enjoy",
        "satisfied",
    }
    NEGATIVE_WORDS = {
        "bad",
        "terrible",
        "awful",
        "hate",
        "sad",
        "horrible",
        "angry",
        "disappointed",
        "frustrated",
        "poor",
    }

    async def analyze(
        self,
        *,
        text: str,
        provider: str,
        model: Optional[str],
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a deterministic sentiment score based on simple heuristics."""

        # simulate asynchronous work so the call path stays consistent with async providers
        await asyncio.sleep(0)

        tokens = re.findall(r"\w+", text.lower())
        positive_hits = sum(1 for token in tokens if token in self.POSITIVE_WORDS)
        negative_hits = sum(1 for token in tokens if token in self.NEGATIVE_WORDS)
        total_hits = positive_hits + negative_hits

        if total_hits == 0:
            sentiment_score = 0.0
        else:
            sentiment_score = (positive_hits - negative_hits) / max(total_hits, 1)

        sentiment_score = max(min(sentiment_score, 1.0), -1.0)
        overall_sentiment = "neutral"
        if sentiment_score > 0.1:
            overall_sentiment = "positive"
        elif sentiment_score < -0.1:
            overall_sentiment = "negative"

        confidence = min(1.0, 0.5 + math.fabs(sentiment_score))

        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_score": sentiment_score,
            "confidence": confidence,
            "emotions": {
                "joy": max(sentiment_score, 0.0),
                "frustration": max(-sentiment_score, 0.0),
            },
            "sentence_sentiments": [],
            "language": language or "en",
            "provider": provider,
            "model": model,
        }


__all__ = ["SimpleSentimentAnalyzer"]


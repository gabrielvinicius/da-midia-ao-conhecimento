"""Application service that orchestrates sentiment analysis providers."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from src.text_analysis.application.services import TextAnalysisService # New import

class SentimentAnalysisService:
    """High-level service coordinating sentiment analysis operations."""

    def __init__(
        self,
        *,
        analyzer: Any,
        repository: Any,
        text_analysis_service: TextAnalysisService, # Injected TextAnalysisService
        logger: Any = None,
        metrics: Any = None,
    ) -> None:
        self._analyzer = analyzer
        self._repository = repository
        self._text_analysis_service = text_analysis_service # Store the injected service
        self._logger = logger
        self._metrics = metrics

    async def analyze_sentiment(
        self,
        *,
        transcription_id: str,
        text: str,
        provider: str,
        model: Optional[str] = None,
        media_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Requests sentiment analysis by scheduling a task."""
        self._log("sentiment_analysis.request.started", transcription_id=transcription_id, provider=provider)
        task_result = await self._text_analysis_service.schedule_sentiment_analysis_task(
            transcription_id=transcription_id,
            text=text,
            provider=provider,
            model=model,
            media_id=media_id,
            language=language
        )
        self._log("sentiment_analysis.request.completed", transcription_id=transcription_id, task_id=task_result.get("task_id"))
        return {
            "success": True,
            "transcription_id": transcription_id,
            "task_id": task_result.get("task_id"),
            "message": "Sentiment analysis task scheduled successfully"
        }

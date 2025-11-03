"""Application service that orchestrates sentiment analysis providers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.text_analysis.application.services import TextAnalysisService

PROCESSING_STATUS = "PROCESSING"


class SentimentAnalysisService:
    """High-level service coordinating sentiment analysis operations."""

    def __init__(
        self,
        *,
        analyzer: Any,
        repository: Any,
        text_analysis_service: TextAnalysisService,
        logger: Any = None,
        metrics: Any = None,
    ) -> None:
        self._analyzer = analyzer
        self._repository = repository
        self._text_analysis_service = text_analysis_service
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
        """Request sentiment analysis by scheduling the background task."""
        self._log(
            "sentiment_analysis.request.started",
            transcription_id=transcription_id,
            provider=provider,
        )
        task_result = await self._text_analysis_service.schedule_sentiment_analysis_task(
            transcription_id=transcription_id,
            text=text,
            provider=provider,
            model=model,
            media_id=media_id,
            language=language,
        )
        task_id = task_result.get("task_id") if isinstance(task_result, dict) else None
        self._log(
            "sentiment_analysis.request.accepted",
            transcription_id=transcription_id,
            task_id=task_id,
        )
        return {
            "success": True,
            "transcription_id": transcription_id,
            "provider": provider,
            "model": model,
            "task_id": task_id,
            "status": PROCESSING_STATUS,
            "message": "Sentiment analysis task scheduled successfully",
        }

    def _log(self, event: str, **kwargs) -> None:
        if not self._logger:
            return
        try:
            self._logger.info(event, **kwargs)
        except Exception:
            # Logging failures shouldn't interrupt API flow.
            pass


__all__ = ["SentimentAnalysisService"]

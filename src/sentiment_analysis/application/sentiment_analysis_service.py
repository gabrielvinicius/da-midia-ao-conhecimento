"""Application service that orchestrates sentiment analysis providers."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class SentimentAnalysisService:
    """High-level service coordinating sentiment analysis operations."""

    def __init__(
        self,
        *,
        analyzer: Any,
        repository: Any,
        logger: Any = None,
        metrics: Any = None,
    ) -> None:
        self._analyzer = analyzer
        self._repository = repository
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
        """Run sentiment analysis using the configured provider."""

        start_time = time.perf_counter()
        self._log("sentiment_analysis.started", transcription_id=transcription_id, provider=provider)

        try:
            payload = await self._analyzer.analyze(
                text=text,
                provider=provider,
                model=model,
                language=language,
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._log(
                "sentiment_analysis.failed",
                level="error",
                transcription_id=transcription_id,
                provider=provider,
                error=str(exc),
            )
            raise

        duration = time.perf_counter() - start_time
        payload.setdefault("provider", provider)
        payload.setdefault("model", model)
        payload.setdefault("media_id", media_id)
        payload.setdefault("processing_time", duration)

        self._record_metrics(provider=provider, duration=duration, success=True)
        self._log(
            "sentiment_analysis.completed",
            transcription_id=transcription_id,
            provider=provider,
            duration=duration,
        )

        return payload

    def _log(self, event: str, level: str = "info", **kwargs: Any) -> None:
        if not self._logger:
            return
        log_method = getattr(self._logger, level, None)
        if callable(log_method):
            log_method(event, **kwargs)

    def _record_metrics(self, *, provider: str, duration: float, success: bool) -> None:
        if not self._metrics:
            return
        if hasattr(self._metrics, "record_operation"):
            self._metrics.record_operation(
                operation="analyze_sentiment",
                provider=provider,
                duration=duration,
                success=success,
            )


__all__ = ["SentimentAnalysisService"]


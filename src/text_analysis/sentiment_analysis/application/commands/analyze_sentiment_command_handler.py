"""Command handler responsible for orchestrating sentiment analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import structlog

from src.media_processing.transcription.domain.transcription import TranscriptionStatus
from src.text_analysis.sentiment_analysis.application.commands.analyze_sentiment_command import (
    AnalyzeSentimentCommand,
)
from src.text_analysis.sentiment_analysis.domain.sentiment_analysis import (
    SentimentAnalysis,
)
from src.shared.exceptions.domain_exceptions import ProcessingError, ValidationError

logger = structlog.get_logger(__name__)


class AnalyzeSentimentCommandHandler:
    """Handle ``AnalyzeSentimentCommand`` messages."""

    def __init__(
        self,
        *,
        sentiment_service: Any,
        analysis_repository: Any,
        transcription_queries: Any,
        connection_manager: Any,
        metrics_service: Any,
    ) -> None:
        self._sentiment_service = sentiment_service
        self._repository = analysis_repository
        self._transcription_queries = transcription_queries
        self._connection_manager = connection_manager
        self._metrics = metrics_service

    async def handle(self, command: AnalyzeSentimentCommand) -> Any:
        """Execute sentiment analysis for the provided transcription."""
        transcription = await self._transcription_queries.get_by_id(command.transcription_id)
        if not transcription:
            raise ValidationError(
                field="transcription_id",
                value=command.transcription_id,
                reason="Transcription not found",
            )

        if getattr(transcription, "status", None) != TranscriptionStatus.COMPLETED:
            raise ValidationError(
                field="transcription_id",
                value=command.transcription_id,
                reason="Transcription not completed",
            )

        transcription_text = (getattr(transcription, "text", "") or "").strip()
        if len(transcription_text) < 10:
            raise ValidationError(
                field="text",
                value="<redacted>",
                reason="Transcription text too short for sentiment analysis",
            )

        if command.schedule_only:
            payload = await self._sentiment_service.analyze_sentiment(
                transcription_id=command.transcription_id,
                text=transcription_text,
                provider=command.provider,
                model=command.model,
                media_id=str(getattr(transcription, "media_id", "")) or None,
                language=command.language,
            )
            return {
                "scheduled": True,
                "task": payload,
            }

        existing = await self._repository.find_by_transcription_id(command.transcription_id)
        if existing:
            logger.info(
                "sentiment_analysis.cached_result",
                transcription_id=command.transcription_id,
                analysis_id=getattr(existing, "id", None),
            )
            return existing

        self._increment_counter("sentiment_analysis.started")
        await self._notify_progress(
            transcription_id=command.transcription_id,
            status="processing",
            progress=0.1,
        )

        try:
            payload = await self._sentiment_service.analyze_sentiment(
                transcription_id=command.transcription_id,
                text=transcription_text,
                provider=command.provider,
                model=command.model,
                media_id=str(getattr(transcription, "media_id", "")) or None,
                language=command.language,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error(
                "sentiment_analysis.failed",
                transcription_id=command.transcription_id,
                error=str(exc),
            )
            self._increment_counter("sentiment_analysis.failed")
            raise ProcessingError("sentiment analysis", str(exc)) from exc

        analysis = SentimentAnalysis(
            media_id=str(getattr(transcription, "media_id", "")) or None,
            transcription_id=str(getattr(transcription, "id", command.transcription_id)),
            provider=payload.get("provider", command.provider),
            model=payload.get("model", command.model),
        )
        analysis.created_at = datetime.utcnow()
        analysis.update_from_payload(payload)

        saved_analysis = await self._repository.save(analysis)

        self._increment_counter("sentiment_analysis.completed")
        processing_time = payload.get("processing_time") or saved_analysis.processing_time
        if processing_time is not None:
            self._record_histogram(
                "sentiment_analysis.processing_time",
                processing_time,
            )

        await self._notify_progress(
            transcription_id=command.transcription_id,
            status="completed",
            progress=1.0,
            analysis_id=saved_analysis.id,
        )

        # EventBus removido: notificação ocorre via ConnectionManager/estado

        return saved_analysis

    def _increment_counter(self, metric: str) -> None:
        if hasattr(self._metrics, "increment_counter"):
            self._metrics.increment_counter(metric)

    def _record_histogram(self, metric: str, value: float) -> None:
        if hasattr(self._metrics, "record_histogram"):
            self._metrics.record_histogram(metric, value)

    async def _notify_progress(
        self,
        *,
        transcription_id: str,
        status: str,
        progress: float,
        analysis_id: Optional[str] = None,
    ) -> None:
        if not self._connection_manager:
            return

        message = {
            "type": "sentiment_analysis_progress",
            "transcription_id": transcription_id,
            "status": status,
            "progress": progress,
        }
        if analysis_id:
            message["analysis_id"] = analysis_id

        try:
            await self._connection_manager.send_personal_message(message)
        except Exception:  # pragma: no cover - progress updates should not fail command
            logger.debug("sentiment_analysis.progress_notification_failed", message=message)

    # EventBus removido: método de publicação não é mais necessário

"""Command handler for processing summaries."""

from __future__ import annotations

import time
from typing import Any, Mapping, Optional
from uuid import UUID

from src.shared.events.domain_events import (
    SummaryCompleted,
    SummarizationProgress,
)
from src.shared.exceptions.domain_exceptions import ProcessingError, ValidationError
from src.summarization.domain.summary import Summary, SummaryStatus
from src.transcription.domain.transcription import TranscriptionStatus

from .process_summary_command import ProcessSummaryCommand


class ProcessSummaryCommandHandler:
    """Coordinates summarization workflow for a single transcription."""

    def __init__(
        self,
        summarizer: Any,
        summary_repo: Any,
        transcription_queries: Optional[Any] = None,
        metrics_service: Optional[Any] = None,
        event_bus: Optional[Any] = None,
        connection_manager: Optional[Any] = None,
    ) -> None:
        self._summarizer = summarizer
        self._summary_repo = summary_repo
        self._transcription_queries = transcription_queries
        self._metrics = metrics_service
        self._event_bus = event_bus
        self._connection_manager = connection_manager

    async def handle(self, command: ProcessSummaryCommand) -> Any:
        """Execute the summarization workflow and persist the result."""

        started_at = time.monotonic()
        transcription_id = command.transcription_id or command.media_id or "unknown"

        self._increment_metric("summarization.started")
        await self._publish_event(
            SummarizationProgress(
                transcription_id=transcription_id,
                progress=0.05,
                message="Summarization started",
            )
        )

        text_content = command.text_content
        media_id = command.media_id

        if text_content is None:
            transcription = await self._fetch_transcription(command)
            text_content = getattr(transcription, "text", "")
            media_id = getattr(transcription, "media_id", media_id)

        if not text_content or len(text_content.strip()) < 20:
            raise ValidationError("text_content", "<redacted>", "Text too short for summarization")

        existing_summary = await self._find_existing_summary(command, media_id)
        if existing_summary and getattr(existing_summary, "status", None) == SummaryStatus.COMPLETED:
            self._increment_metric("summarization.completed")
            return existing_summary

        try:
            summary_payload = await self._summarize(text_content, command)
        except Exception as exc:  # pragma: no cover - defensive safeguard
            await self._publish_event(
                SummarizationProgress(
                    transcription_id=transcription_id,
                    progress=1.0,
                    message="Summarization failed",
                )
            )
            self._increment_metric("summarization.failed")
            raise ProcessingError("summarization", f"Summarization failed: {exc}") from exc

        summary_entity = await self._persist_summary(
            media_id=media_id,
            provider=command.provider,
            summary_payload=summary_payload,
            existing=existing_summary,
        )

        await self._publish_event(
            SummarizationProgress(
                transcription_id=transcription_id,
                progress=1.0,
                message="Summarization completed",
            )
        )
        await self._publish_event(
            SummaryCompleted(
                summary_id=str(getattr(summary_entity, "id", "")),
                transcription_id=transcription_id,
                provider=command.provider,
                status=getattr(summary_entity, "status", None),
            )
        )

        if self._connection_manager is not None and hasattr(self._connection_manager, "send_personal_message"):
            await self._connection_manager.send_personal_message(
                transcription_id,
                {
                    "event": "summary_completed",
                    "summary_id": str(getattr(summary_entity, "id", "")),
                    "provider": command.provider,
                },
            )

        duration = time.monotonic() - started_at
        self._record_histogram("summarization.duration", duration)
        self._increment_metric("summarization.completed")

        return summary_entity

    async def _fetch_transcription(self, command: ProcessSummaryCommand) -> Any:
        if self._transcription_queries is None:
            raise ValidationError("transcription_queries", "None", "Transcription queries dependency not configured")
        if not command.transcription_id:
            raise ValidationError("transcription_id", "", "Transcription ID is required when text is not provided")

        transcription = await self._transcription_queries.get_by_id(command.transcription_id)
        if transcription is None:
            raise ValidationError("transcription_id", command.transcription_id, "Transcription not found")

        status = getattr(transcription, "status", None)
        if status != TranscriptionStatus.COMPLETED:
            raise ValidationError("transcription_status", status, "Transcription not completed")

        return transcription

    async def _find_existing_summary(self, command: ProcessSummaryCommand, media_id: Optional[str]) -> Optional[Any]:
        repository_method = None

        if command.transcription_id and hasattr(self._summary_repo, "find_by_transcription_id"):
            repository_method = getattr(self._summary_repo, "find_by_transcription_id")
            return await repository_method(command.transcription_id)

        if media_id and hasattr(self._summary_repo, "get_by_media_id"):
            repository_method = getattr(self._summary_repo, "get_by_media_id")
            return await repository_method(self._coerce_uuid(media_id))

        return None

    async def _summarize(self, text: str, command: ProcessSummaryCommand) -> Mapping[str, Any]:
        options = command.options or {}
        if command.strategy:
            options.setdefault("strategy", command.strategy)
        if command.max_length:
            options.setdefault("max_length", command.max_length)

        result = await self._summarizer.summarize(text, options=options)
        if isinstance(result, Mapping):
            return result
        return {"text": result}

    async def _persist_summary(
        self,
        *,
        media_id: Optional[str],
        provider: str,
        summary_payload: Mapping[str, Any],
        existing: Optional[Any],
    ) -> Any:
        summary_entity = existing or self._build_summary(media_id=media_id, provider=provider)
        text = str(summary_payload.get("text", ""))
        summary_entity.mark_as_completed(text)
        if hasattr(summary_entity, "provider"):
            summary_entity.provider = provider

        for attribute in ("strategy", "bullet_points", "key_topics", "confidence_score", "processing_time"):
            if attribute in summary_payload and hasattr(summary_entity, attribute):
                setattr(summary_entity, attribute, summary_payload[attribute])

        if existing is None:
            if hasattr(self._summary_repo, "add"):
                await self._summary_repo.add(summary_entity)
        else:
            if hasattr(self._summary_repo, "update"):
                await self._summary_repo.update(summary_entity)

        if hasattr(self._summary_repo, "save"):
            return await self._summary_repo.save(summary_entity)

        return summary_entity

    def _build_summary(self, *, media_id: Optional[str], provider: str) -> Summary:
        summary = Summary.create(media_id=media_id or "", provider=provider)
        if hasattr(summary, "status"):
            summary.status = SummaryStatus.PROCESSING
        return summary

    async def _publish_event(self, event: SummarizationProgress | SummaryCompleted) -> None:
        if self._event_bus is not None and hasattr(self._event_bus, "publish"):
            await self._event_bus.publish(event)

    def _increment_metric(self, name: str) -> None:
        if self._metrics is not None and hasattr(self._metrics, "increment_counter"):
            self._metrics.increment_counter(name)

    def _record_histogram(self, name: str, value: float) -> None:
        if self._metrics is not None and hasattr(self._metrics, "record_histogram"):
            self._metrics.record_histogram(name, value)

    @staticmethod
    def _coerce_uuid(value: Any) -> Any:
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return value


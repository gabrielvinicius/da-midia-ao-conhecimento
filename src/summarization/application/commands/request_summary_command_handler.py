"""Command handler responsible for triggering summary generation."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping, Optional

from src.shared.events.domain_events import SummarizationRequested

from .request_summary_command import RequestSummaryCommand


class RequestSummaryCommandHandler:
    """Publishes a :class:`SummarizationRequested` event to kick off processing."""

    def __init__(
        self,
        event_bus: Any,
        task_scheduler: Optional[Any] = None,
    ) -> None:
        self._event_bus = event_bus
        self._task_scheduler = task_scheduler

    async def handle(self, command: RequestSummaryCommand) -> Mapping[str, Any]:
        """Dispatch the request and optionally schedule background processing."""

        event = SummarizationRequested(
            transcription_id=command.transcription_id,
            provider=command.provider,
            strategy=command.strategy,
        )

        if self._event_bus is not None:
            await self._event_bus.publish(event)

        task_id: Optional[str] = None
        if self._task_scheduler is not None:
            task_result = await self._task_scheduler.schedule_summarization_task(
                media_id=command.transcription_id,
                text_content="",
                provider=command.provider,
            )
            if isinstance(task_result, Mapping):
                task_id = str(task_result.get("task_id")) if task_result.get("task_id") else None

        payload = asdict(command)
        payload.pop("strategy", None)

        return {
            "status": "ACCEPTED",
            "task_id": task_id,
            "command": payload,
        }


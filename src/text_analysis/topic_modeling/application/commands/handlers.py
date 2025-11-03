"""Command handlers for topic modeling workflows."""

from __future__ import annotations

from typing import Dict
from uuid import UUID

from src.text_analysis.topic_modeling.application.commands.commands import (
    AnalyzeTopicsCommand,
)
from src.text_analysis.topic_modeling.application.topic_modeling_service import (
    TopicModelingService,
)


class AnalyzeTopicsCommandHandler:
    """Handle analyze topic commands by orchestrating the service layer."""

    def __init__(self, topic_modeling_service: TopicModelingService) -> None:
        self._service = topic_modeling_service

    async def handle(self, command: AnalyzeTopicsCommand) -> Dict[str, object]:
        """Execute topic modeling analysis or schedule it for later execution."""

        media_id = UUID(command.media_id)

        if command.should_schedule_only():
            task_info = await self._service.request_topic_analysis(
                media_id=media_id,
                text_content=command.text_content,
                provider=command.provider,
                language=command.language,
            )

            return {
                "media_id": str(media_id),
                "scheduled": True,
                "task": task_info,
            }

        topic_result = await self._service.analyze_topics(
            media_id=media_id,
            text_content=command.text_content,
            provider=command.provider,
            language=command.language,
            options=command.options,
        )

        return {
            "scheduled": False,
            "media_id": str(topic_result.media_id),
            "result_id": str(topic_result.id),
            "status": topic_result.status.value,
            "topics": topic_result.topics,
        }


__all__ = ["AnalyzeTopicsCommandHandler"]

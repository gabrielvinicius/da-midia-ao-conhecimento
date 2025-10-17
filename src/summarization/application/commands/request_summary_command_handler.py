# src/summarization/application/commands/request_summary_command_handler.py
import structlog

from src.shared.events.domain_events import SummarizationRequested
from src.shared.events.event_bus import EventBus
from src.summarization.application.commands.request_summary_command import RequestSummaryCommand

logger = structlog.get_logger(__name__)


class RequestSummaryCommandHandler:
    """Handler for the RequestSummaryCommand."""
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def handle(self, command: RequestSummaryCommand) -> None:
        """Dispatches a SummarizationRequested event to the event bus."""
        logger.info(
            "summary.requested",
            transcription_id=command.transcription_id,
            provider=command.provider
        )
        event = SummarizationRequested(
            transcription_id=command.transcription_id,
            provider=command.provider
        )
        await self.event_bus.publish(event)

# src/sentiment_analysis/application/commands/analyze_sentiment_command_handler.py
import structlog

from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import SentimentAnalysisRepository
from src.sentiment_analysis.infrastructure.dependencies import SentimentServiceFactory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import SentimentAnalysisCompleted
from .analyze_sentiment_command import AnalyzeSentimentCommand

logger = structlog.get_logger(__name__)


class AnalyzeSentimentCommandHandler:
    def __init__(
        self,
        sentiment_service_factory: SentimentServiceFactory,
        repository: SentimentAnalysisRepository,
        event_bus: EventBus,
    ):
        self.sentiment_service_factory = sentiment_service_factory
        self.repository = repository
        self.event_bus = event_bus

    async def handle(self, command: AnalyzeSentimentCommand) -> SentimentAnalysisResult:
        """Handles the sentiment analysis process."""
        logger.info("sentiment_analysis.started", media_id=command.media_id, provider=command.provider)

        try:
            service = self.sentiment_service_factory(command.provider)
            analysis_data = service.analyze(command.text_content)

            result = SentimentAnalysisResult(
                media_id=command.media_id,
                label=analysis_data.get("label"),
                score=analysis_data.get("score"),
                full_result=analysis_data
            )

            saved_result = await self.repository.save(result)

            await self.event_bus.publish(SentimentAnalysisCompleted(
                media_id=command.media_id,
                sentiment_result=analysis_data
            ))

            logger.info("sentiment_analysis.completed", media_id=command.media_id)
            return saved_result

        except Exception as e:
            logger.error("sentiment_analysis.failed", media_id=command.media_id, error=str(e))
            # In a real scenario, you might want to save a FAILED state.
            raise

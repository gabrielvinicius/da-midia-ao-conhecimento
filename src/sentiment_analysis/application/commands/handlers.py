# src/sentiment_analysis/application/commands/handlers.py
import structlog
from typing import Dict, Any
from uuid import UUID
import time # Adicionar para calcular duração

from src.sentiment_analysis.domain.interfaces import (
    ISentimentAnalyzer,
    ISentimentAnalysisRepository,
    SentimentOperationLogger,
    SentimentMetrics
)
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult # Importar a entidade
from src.sentiment_analysis.application.commands.commands import AnalyzeSentimentCommand

logger = structlog.get_logger(__name__)


class AnalyzeSentimentCommandHandler:
    """Handler for analyzing sentiment of a text."""

    def __init__(
        self,
        sentiment_analyzer: ISentimentAnalyzer,
        sentiment_analysis_repo: ISentimentAnalysisRepository,
        sentiment_logger: SentimentOperationLogger,
        sentiment_metrics: SentimentMetrics
    ):
        self.sentiment_analyzer = sentiment_analyzer
        self.sentiment_analysis_repo = sentiment_analysis_repo
        self.sentiment_logger = sentiment_logger
        self.sentiment_metrics = sentiment_metrics

    async def handle(self, command: AnalyzeSentimentCommand) -> Dict[str, Any]:
        start_time = time.monotonic()
        operation_name = "analyze_sentiment_command"
        success = False
        error = None
        result_id_str = ""
        output_score = 0.0

        logger.info(
            f"sentiment_analysis.{operation_name}.started",
            media_id=command.media_id,
            provider=command.provider,
            language=command.language
        )
        try:
            # 1. Perform sentiment analysis
            analysis_data = await self.sentiment_analyzer.analyze(
                text_content=command.text_content,
                language=command.language,
                options=command.options
            )
            output_score = analysis_data.get("score", 0.0)

            # 2. Create or update SentimentAnalysisResult entity
            # Assumindo que queremos um resultado único por media_id
            existing_result = await self.sentiment_analysis_repo.get_by_media_id(UUID(command.media_id))

            if existing_result:
                existing_result.update_from_analysis(analysis_data)
                await self.sentiment_analysis_repo.update(existing_result)
                sentiment_result = existing_result
            else:
                sentiment_result = SentimentAnalysisResult(
                    media_id=UUID(command.media_id),
                    label=analysis_data.get("label"),
                    score=analysis_data.get("score"),
                    confidence=analysis_data.get("confidence"),
                    provider=analysis_data.get("provider"),
                    model_name=analysis_data.get("model_name"),
                    processing_time_ms=analysis_data.get("processing_time_ms"),
                    text_length=analysis_data.get("text_length"),
                    language=analysis_data.get("language"),
                    granularity=analysis_data.get("granularity"),
                    full_result=analysis_data.get("full_result"),
                    detailed_scores=analysis_data.get("detailed_scores"),
                    emotions=analysis_data.get("emotions"),
                    keywords=analysis_data.get("keywords"),
                    is_reliable=analysis_data.get("is_reliable", True),
                    error_message=analysis_data.get("error_message")
                )
                await self.sentiment_analysis_repo.add(sentiment_result)
            
            result_id_str = str(sentiment_result.id)
            success = True

            logger.info(
                f"sentiment_analysis.{operation_name}.completed",
                media_id=command.media_id,
                result_id=result_id_str,
                label=sentiment_result.label,
                score=sentiment_result.score
            )
            return {
                "success": True,
                "media_id": command.media_id,
                "result_id": result_id_str,
                "label": sentiment_result.label,
                "score": sentiment_result.score,
                "message": "Sentiment analysis completed successfully"
            }
        except Exception as e:
            error = e
            logger.error(
                f"sentiment_analysis.{operation_name}.failed",
                media_id=command.media_id,
                error=str(e)
            )
            # TODO: Marcar o resultado da análise como falho no repositório, se aplicável
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.sentiment_logger.log_operation(
                operation=operation_name,
                media_id=command.media_id,
                provider=command.provider,
                success=success,
                duration=duration,
                error=error
            )
            await self.sentiment_metrics.record_operation(
                operation=operation_name,
                provider=command.provider,
                duration=duration,
                success=success,
                input_text_length_chars=len(command.text_content),
                output_score=output_score
            )

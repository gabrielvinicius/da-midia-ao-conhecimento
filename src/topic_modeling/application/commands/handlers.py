# src/topic_modeling/application/commands/handlers.py
import structlog
from typing import Dict, Any
from uuid import UUID
import time # Adicionar para calcular duração

from src.topic_modeling.domain.interfaces import (
    ITopicModeler,
    ITopicModelingRepository,
    TopicModelingOperationLogger,
    TopicModelingMetrics
)
from src.topic_modeling.domain.topic_modeling import TopicModelingResult # Importar a entidade
from src.topic_modeling.application.commands.commands import AnalyzeTopicsCommand

logger = structlog.get_logger(__name__)


class AnalyzeTopicsCommandHandler:
    """Handler for analyzing topics of a text."""

    def __init__(
        self,
        topic_modeler: ITopicModeler,
        topic_modeling_repo: ITopicModelingRepository,
        topic_logger: TopicModelingOperationLogger,
        topic_metrics: TopicModelingMetrics
    ):
        self.topic_modeler = topic_modeler
        self.topic_modeling_repo = topic_modeling_repo
        self.topic_logger = topic_logger
        self.topic_metrics = topic_metrics

    async def handle(self, command: AnalyzeTopicsCommand) -> Dict[str, Any]:
        start_time = time.monotonic()
        operation_name = "analyze_topics_command"
        success = False
        error = None
        result_id_str = ""
        num_topics = 0

        logger.info(
            f"topic_modeling.{operation_name}.started",
            media_id=command.media_id,
            provider=command.provider,
            language=command.language
        )
        try:
            # 1. Perform topic modeling
            modeling_data = await self.topic_modeler.model_topics(
                text_content=command.text_content,
                language=command.language,
                options=command.options
            )
            num_topics = modeling_data.get("num_topics", 0)

            # 2. Create or update TopicModelingResult entity
            # Assumindo que queremos um resultado único por media_id
            existing_result = await self.topic_modeling_repo.get_by_media_id(UUID(command.media_id))

            if existing_result:
                existing_result.mark_as_completed(modeling_data.get("topics", {})) # Atualizar tópicos
                await self.topic_modeling_repo.update(existing_result)
                topic_result = existing_result
            else:
                topic_result = TopicModelingResult.create(
                    media_id=UUID(command.media_id),
                    provider=command.provider
                )
                topic_result.mark_as_completed(modeling_data.get("topics", {}))
                await self.topic_modeling_repo.add(topic_result)
            
            result_id_str = str(topic_result.id)
            success = True

            logger.info(
                f"topic_modeling.{operation_name}.completed",
                media_id=command.media_id,
                result_id=result_id_str,
                num_topics=num_topics
            )
            return {
                "success": True,
                "media_id": command.media_id,
                "result_id": result_id_str,
                "num_topics": num_topics,
                "message": "Topic modeling completed successfully"
            }
        except Exception as e:
            error = e
            logger.error(
                f"topic_modeling.{operation_name}.failed",
                media_id=command.media_id,
                error=str(e)
            )
            # TODO: Marcar o resultado da análise como falho no repositório, se aplicável
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.topic_logger.log_operation(
                operation=operation_name,
                media_id=command.media_id,
                provider=command.provider,
                success=success,
                duration=duration,
                error=error
            )
            await self.topic_metrics.record_operation(
                operation=operation_name,
                provider=command.provider,
                duration=duration,
                success=success,
                input_text_length_chars=len(command.text_content),
                num_topics=num_topics
            )

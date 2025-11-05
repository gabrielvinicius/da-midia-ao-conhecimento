# src/text_processing/bootstrap.py
from dataclasses import dataclass

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.infrastructure.dependencies import StorageServiceFactory

# Consolidated Service
from src.text_analysis.text_processing.application.text_processing_service import (
    TextProcessingService,
)
from src.text_analysis.text_processing.infrastructure.pipelines.extraction_pipeline import (
    TextExtractionPipelineFactory,
)
from src.text_analysis.text_processing.infrastructure.task_scheduler import (
    CeleryTextProcessingTaskScheduler,
)
from src.text_analysis.text_processing.infrastructure.text_extractor import (
    TextExtractor,
)

# Concrete Implementations
from src.text_analysis.text_processing.infrastructure.text_processor import (
    TextProcessor,
)

# TODO: Adicionar logger e metrics específicos para text_processing


class TextProcessingContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    storage_factory: providers.Provider[StorageServiceFactory] = providers.Dependency()
    storage_provider = providers.Dependency(default="local")

    # Pipelines de extração
    basic_extraction_pipeline = providers.Singleton(
        TextExtractionPipelineFactory.create_basic_pipeline
    )
    advanced_extraction_pipeline = providers.Singleton(
        TextExtractionPipelineFactory.create_advanced_pipeline,
    )

    # Infrastructure Services
    text_processor = providers.Factory(TextProcessor)
    text_extractor = providers.Factory(
        TextExtractor,
        basic_extraction_pipeline=basic_extraction_pipeline,
        advanced_extraction_pipeline=advanced_extraction_pipeline,
        storage_factory=storage_factory,
        default_storage_provider=storage_provider,
    )
    text_processing_task_scheduler = providers.Factory(CeleryTextProcessingTaskScheduler)
    # TODO: Adicionar text_processing_logger, text_processing_metrics

    # Consolidated Application Service
    text_processing_service = providers.Factory(
        TextProcessingService,
        text_processor=text_processor,
        text_extractor=text_extractor,
        task_scheduler=text_processing_task_scheduler,
        # TODO: Adicionar text_processing_logger, text_processing_metrics
    )


@dataclass
class TextProcessingModule:
    service: TextProcessingService
    task_scheduler: CeleryTextProcessingTaskScheduler


async def build_text_processing_module(
    session: AsyncSession,
    *,
    storage_factory: StorageServiceFactory | None = None,
    storage_provider: str = "local",
) -> TextProcessingModule:
    storage_factory = storage_factory or StorageServiceFactory()
    container = TextProcessingContainer(
        db=session,
        storage_factory=storage_factory,
        storage_provider=storage_provider,
    )
    module = TextProcessingModule(
        service=container.text_processing_service(),
        task_scheduler=container.text_processing_task_scheduler(),
    )
    return module


__all__ = [
    "TextProcessingContainer",
    "TextProcessingModule",
    "build_text_processing_module",
]

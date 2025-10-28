# src/text_processing/bootstrap.py
from dataclasses import dataclass
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.text_processing.infrastructure.text_processor import TextProcessor
from src.text_processing.infrastructure.text_extractor import TextExtractor
from src.text_processing.infrastructure.task_scheduler import CeleryTextProcessingTaskScheduler
from src.text_processing.infrastructure.pipelines.extraction_pipeline import TextExtractionPipelineFactory
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
# TODO: Adicionar logger e metrics específicos para text_processing

# Consolidated Service
from src.text_processing.application.text_processing_service import TextProcessingService


class TextProcessingContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    s3_storage_service: providers.Provider[S3StorageService] = providers.Singleton(S3StorageService)

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
        s3_storage_service=s3_storage_service
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


def build_text_processing_module(session: AsyncSession) -> TextProcessingModule:
    container = TextProcessingContainer(db=session)
    return TextProcessingModule(
        service=container.text_processing_service(),
        task_scheduler=container.text_processing_task_scheduler(),
    )

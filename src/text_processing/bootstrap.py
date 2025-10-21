# src/text_processing/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.text_processing.domain.interfaces import ITextProcessor, ITextExtractor, ITextProcessingTaskScheduler
from src.text_processing.infrastructure.text_processor import TextProcessor
from src.text_processing.infrastructure.text_extractor import TextExtractor
from src.text_processing.infrastructure.task_scheduler import CeleryTextProcessingTaskScheduler
from src.text_processing.application.commands.handlers import ProcessTextCommandHandler, ExtractTextCommandHandler
from src.text_processing.infrastructure.pipelines.extraction_pipeline import TextExtractionPipelineFactory # Adicionar
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService # Adicionar

class TextProcessingContainer(containers.DeclarativeContainer):
    # Configuração de wiring, se houver routers ou dependências FastAPI
    # wiring_config = containers.WiringConfiguration(modules=[])

    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()
    s3_storage_service: providers.Provider[S3StorageService] = providers.Singleton(S3StorageService) # Adicionar

    # Pipelines de extração
    basic_extraction_pipeline = providers.Singleton(
        TextExtractionPipelineFactory.create_basic_pipeline
    )
    advanced_extraction_pipeline = providers.Singleton(
        TextExtractionPipelineFactory.create_advanced_pipeline,
        # pdf_extractor=..., # Se houver extratores específicos para injetar
        # docx_extractor=...,
    )

    # Implementações concretas das interfaces de domínio
    text_processor: providers.Provider[ITextProcessor] = providers.Factory(
        TextProcessor
    )
    text_extractor: providers.Provider[ITextExtractor] = providers.Factory(
        TextExtractor,
        basic_extraction_pipeline=basic_extraction_pipeline,
        advanced_extraction_pipeline=advanced_extraction_pipeline,
        s3_storage_service=s3_storage_service
    )
    text_processing_task_scheduler: providers.Provider[ITextProcessingTaskScheduler] = providers.Factory(
        CeleryTextProcessingTaskScheduler
    )

    # Command Handlers
    process_text_command_handler: providers.Provider[ProcessTextCommandHandler] = providers.Factory(
        ProcessTextCommandHandler,
        text_processor=text_processor
    )
    extract_text_command_handler: providers.Provider[ExtractTextCommandHandler] = providers.Factory(
        ExtractTextCommandHandler,
        text_extractor=text_extractor
    )
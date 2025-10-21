# src/text_processing/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession # Manter se necessário para o db
from typing import Dict, Any

from src.text_processing.domain.interfaces import ITextProcessor, ITextExtractor, ITextProcessingTaskScheduler # Adicionar ITextProcessingTaskScheduler
from src.text_processing.infrastructure.text_processor import TextProcessor
from src.text_processing.infrastructure.text_extractor import TextExtractor
from src.text_processing.infrastructure.task_scheduler import CeleryTextProcessingTaskScheduler # Adicionar CeleryTextProcessingTaskScheduler
from src.text_processing.application.commands.handlers import ProcessTextCommandHandler, ExtractTextCommandHandler

class TextProcessingContainer(containers.DeclarativeContainer):
    # Configuração de wiring, se houver routers ou dependências FastAPI
    # wiring_config = containers.WiringConfiguration(modules=[]) # Não há routers FastAPI diretamente neste módulo

    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Implementações concretas das interfaces de domínio
    text_processor: providers.Provider[ITextProcessor] = providers.Factory(
        TextProcessor
    )
    text_extractor: providers.Provider[ITextExtractor] = providers.Factory(
        TextExtractor
    )
    text_processing_task_scheduler: providers.Provider[ITextProcessingTaskScheduler] = providers.Factory( # Adicionar este provedor
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

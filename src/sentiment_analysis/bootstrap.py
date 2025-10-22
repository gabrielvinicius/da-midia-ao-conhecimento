# src/sentiment_analysis/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.sentiment_analysis.domain.interfaces import (
    ISentimentAnalyzer,
    ISentimentAnalysisRepository,
    ISentimentAnalysisTaskScheduler,
    SentimentOperationLogger,
    SentimentMetrics
)
from src.sentiment_analysis.infrastructure.sentiment_analyzer import HuggingFaceSentimentAnalyzer
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import SentimentAnalysisRepository
from src.sentiment_analysis.infrastructure.task_scheduler import CelerySentimentAnalysisTaskScheduler
from src.sentiment_analysis.infrastructure.logging import StructuredSentimentLogger
from src.sentiment_analysis.infrastructure.metrics import PrometheusSentimentMetrics
from src.sentiment_analysis.application.commands.handlers import AnalyzeSentimentCommandHandler
from src.sentiment_analysis.application.sentiment_analysis_service import SentimentAnalysisService

class SentimentAnalysisContainer(containers.DeclarativeContainer):
    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Implementações concretas das interfaces de domínio
    sentiment_analyzer: providers.Provider[ISentimentAnalyzer] = providers.Factory(
        HuggingFaceSentimentAnalyzer
    )
    sentiment_analysis_repository: providers.Provider[ISentimentAnalysisRepository] = providers.Factory(
        SentimentAnalysisRepository,
        db=db
    )
    sentiment_analysis_task_scheduler: providers.Provider[ISentimentAnalysisTaskScheduler] = providers.Factory(
        CelerySentimentAnalysisTaskScheduler
    )
    sentiment_logger: providers.Provider[SentimentOperationLogger] = providers.Singleton(
        StructuredSentimentLogger
    )
    sentiment_metrics: providers.Provider[SentimentMetrics] = providers.Singleton(
        PrometheusSentimentMetrics
    )

    # Command Handlers
    analyze_sentiment_command_handler: providers.Provider[AnalyzeSentimentCommandHandler] = providers.Factory(
        AnalyzeSentimentCommandHandler,
        sentiment_analyzer=sentiment_analyzer,
        sentiment_analysis_repo=sentiment_analysis_repository,
        sentiment_logger=sentiment_logger,
        sentiment_metrics=sentiment_metrics
    )

    # Serviços de Aplicação
    sentiment_analysis_service: providers.Provider[SentimentAnalysisService] = providers.Factory(
        SentimentAnalysisService,
        sentiment_analyzer=sentiment_analyzer,
        sentiment_analysis_repo=sentiment_analysis_repository,
        task_scheduler=sentiment_analysis_task_scheduler,
        sentiment_logger=sentiment_logger,
        sentiment_metrics=sentiment_metrics
    )
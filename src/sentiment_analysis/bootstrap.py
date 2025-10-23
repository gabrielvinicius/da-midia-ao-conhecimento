# src/sentiment_analysis/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import SentimentAnalysisRepository
from src.sentiment_analysis.infrastructure.sentiment_analyzer import HuggingFaceSentimentAnalyzer
from src.sentiment_analysis.infrastructure.task_scheduler import CelerySentimentAnalysisTaskScheduler
from src.sentiment_analysis.infrastructure.logging import StructuredSentimentLogger
from src.sentiment_analysis.infrastructure.metrics import PrometheusSentimentMetrics

# Consolidated Service
from src.sentiment_analysis.application.sentiment_analysis_service import SentimentAnalysisService

class SentimentAnalysisContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Infrastructure Services
    sentiment_analysis_repository = providers.Factory(SentimentAnalysisRepository, db=db)
    sentiment_analyzer = providers.Factory(HuggingFaceSentimentAnalyzer)
    sentiment_analysis_task_scheduler = providers.Factory(CelerySentimentAnalysisTaskScheduler)
    sentiment_logger = providers.Singleton(StructuredSentimentLogger)
    sentiment_metrics = providers.Singleton(PrometheusSentimentMetrics)

    # Consolidated Application Service
    sentiment_analysis_service = providers.Factory(
        SentimentAnalysisService,
        sentiment_analyzer=sentiment_analyzer,
        sentiment_analysis_repo=sentiment_analysis_repository,
        task_scheduler=sentiment_analysis_task_scheduler,
        sentiment_logger=sentiment_logger,
        sentiment_metrics=sentiment_metrics
    )

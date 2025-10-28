"""Helpers to register module dependencies within the FastAPI application."""

from fastapi import FastAPI

from src.admin.api.dependencies import (
    AdminDependencies,
    get_admin_dependencies,
)
from src.admin.bootstrap import AdminModule
from src.auth.api.dependencies import AuthDependencies, get_auth_dependencies
from src.auth.bootstrap import AuthModule
from src.media_management.api.dependencies import (
    MediaDependencies,
    get_media_dependencies,
)
from src.media_management.bootstrap import MediaModule
from src.monitoring.api.dependencies import (
    MonitoringDependencies,
    get_monitoring_dependencies,
)
from src.monitoring.bootstrap import MonitoringModule
from src.notifications.api.dependencies import (
    NotificationDependencies,
    get_notification_dependencies,
)
from src.notifications.bootstrap import NotificationModule
from src.providers.api.dependencies import get_provider_registry
from src.providers.bootstrap import ProvidersModule
from src.sentiment_analysis.api.dependencies import (
    SentimentDependencies,
    get_sentiment_dependencies,
)
from src.sentiment_analysis.bootstrap import SentimentAnalysisModule
from src.summarization.api.dependencies import (
    SummarizationDependencies,
    get_summarization_dependencies,
)
from src.summarization.bootstrap import SummarizationModule
from src.topic_modeling.api.dependencies import (
    TopicModelingDependencies,
    get_topic_modeling_dependencies,
)
from src.topic_modeling.bootstrap import TopicModelingModule
from src.transcription.api.dependencies import (
    TranscriptionDependencies,
    get_transcription_dependencies,
)
from src.transcription.bootstrap import TranscriptionModule


def register_module_dependencies(
    app: FastAPI,
    *,
    auth: AuthModule,
    monitoring: MonitoringModule,
    media: MediaModule,
    transcription: TranscriptionModule,
    notifications: NotificationModule,
    summarization: SummarizationModule,
    providers: ProvidersModule,
    sentiment_analysis: SentimentAnalysisModule,
    topic_modeling: TopicModelingModule,
    admin: AdminModule,
) -> None:
    """Register application dependencies using FastAPI overrides."""

    app.dependency_overrides[get_auth_dependencies] = lambda: AuthDependencies(
        user_service=auth.user_service,
        auth_service=auth.auth_service,
        auth_queries=auth.auth_queries,
        settings=auth.settings,
    )

    app.dependency_overrides[get_monitoring_dependencies] = (
        lambda: MonitoringDependencies(
            analytics_queries=monitoring.analytics_queries,
            metrics_service=monitoring.metrics_service,
        )
    )

    app.dependency_overrides[get_media_dependencies] = lambda: MediaDependencies(
        queries=media.queries,
        upload_service=media.upload_service,
        lifecycle_service=media.lifecycle_service,
        query_service=media.query_service,
    )

    app.dependency_overrides[get_transcription_dependencies] = (
        lambda: TranscriptionDependencies(
            service=transcription.service,
            queries=transcription.queries,
        )
    )

    app.dependency_overrides[get_notification_dependencies] = (
        lambda: NotificationDependencies(
            service=notifications.service,
            queries=notifications.queries,
        )
    )

    app.dependency_overrides[get_summarization_dependencies] = (
        lambda: SummarizationDependencies(
            service=summarization.service,
        )
    )

    app.dependency_overrides[get_provider_registry] = lambda: providers.provider_registry

    app.dependency_overrides[get_sentiment_dependencies] = (
        lambda: SentimentDependencies(
            service=sentiment_analysis.service,
            repository=sentiment_analysis.repository,
        )
    )

    app.dependency_overrides[get_topic_modeling_dependencies] = (
        lambda: TopicModelingDependencies(
            service=topic_modeling.service,
            repository=topic_modeling.repository,
        )
    )

    app.dependency_overrides[get_admin_dependencies] = lambda: AdminDependencies(
        admin_queries=admin.admin_queries,
        audit_service=admin.audit_service,
        user_service=admin.user_service,
        media_service=admin.media_service,
    )

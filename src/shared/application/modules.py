"""Helpers to register module dependencies within the FastAPI application."""

from fastapi import FastAPI

from src.admin.api.dependencies import (
    AdminDependencies,
    get_admin_dependencies,
)
from src.admin.bootstrap import AdminModule
from src.user_management.api.dependencies import AuthDependencies, get_auth_dependencies
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
try:  # noqa: SIM105 - optional during refactor
    from src.sentiment_analysis.api.dependencies import (
        SentimentDependencies,
        get_sentiment_dependencies,
    )
    from src.sentiment_analysis.bootstrap import SentimentAnalysisModule
except Exception:  # pragma: no cover
    SentimentDependencies = None  # type: ignore[assignment]
    get_sentiment_dependencies = None  # type: ignore[assignment]
    SentimentAnalysisModule = None  # type: ignore[assignment]
try:  # noqa: SIM105 - optional during refactor
    from src.summarization.api.dependencies import (
        SummarizationDependencies,
        get_summarization_dependencies,
    )
    from src.summarization.bootstrap import SummarizationModule
except Exception:  # pragma: no cover
    SummarizationDependencies = None  # type: ignore[assignment]
    get_summarization_dependencies = None  # type: ignore[assignment]
    SummarizationModule = None  # type: ignore[assignment]
try:  # noqa: SIM105 - optional during refactor
    from src.topic_modeling.api.dependencies import (
        TopicModelingDependencies,
        get_topic_modeling_dependencies,
    )
    from src.topic_modeling.bootstrap import TopicModelingModule
except Exception:  # pragma: no cover
    TopicModelingDependencies = None  # type: ignore[assignment]
    get_topic_modeling_dependencies = None  # type: ignore[assignment]
    TopicModelingModule = None  # type: ignore[assignment]
from src.media_processing.transcription.api.dependencies import (
    TranscriptionDependencies,
    get_transcription_dependencies,
)
from src.user_management.bootstrap import UserManagementModule


def register_module_dependencies(
    app: FastAPI,
    *,
        auth: UserManagementModule,
    monitoring: MonitoringModule,
    media: MediaModule,
    notifications: NotificationModule,
    summarization: object | None,
    providers: ProvidersModule,
    sentiment_analysis: object | None,
    topic_modeling: object | None,
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
            service=media.transcription_service,
            queries=media.transcription_queries,
        )
    )

    app.dependency_overrides[get_notification_dependencies] = (
        lambda: NotificationDependencies(
            service=notifications.service,
            queries=notifications.queries,
        )
    )

    if SummarizationDependencies is not None and get_summarization_dependencies is not None and summarization is not None:
        app.dependency_overrides[get_summarization_dependencies] = (
            lambda: SummarizationDependencies(
                service=summarization.service,
            )
        )

    app.dependency_overrides[get_provider_registry] = lambda: providers.provider_registry

    if SentimentDependencies is not None and get_sentiment_dependencies is not None and sentiment_analysis is not None:
        app.dependency_overrides[get_sentiment_dependencies] = (
            lambda: SentimentDependencies(
                service=sentiment_analysis.service,
                repository=sentiment_analysis.repository,
            )
        )

    if TopicModelingDependencies is not None and get_topic_modeling_dependencies is not None and topic_modeling is not None:
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
        facade=admin.facade,
        facade_enabled=admin.facade_enabled,
    )

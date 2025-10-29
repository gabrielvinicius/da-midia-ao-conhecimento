from contextlib import asynccontextmanager
from types import SimpleNamespace
import os

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
# OpenTelemetry Imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.admin.bootstrap import build_admin_module
from src.media_management.bootstrap import build_media_components
from src.monitoring.bootstrap import build_monitoring_module
from src.notifications.bootstrap import build_notification_module
from src.notifications.infrastructure.connection_manager import manager
from src.providers.bootstrap import build_providers_module
# Optional modules (may fail during bootstrap while legacy code is refactored)
try:  # noqa: SIM105 - tolerate partial availability
    from src.sentiment_analysis.bootstrap import build_sentiment_analysis_module
except Exception as _sentiment_import_error:  # pragma: no cover - fallback path
    build_sentiment_analysis_module = None  # type: ignore[assignment]
else:
    _sentiment_import_error = None
from src.shared.application.lifecycle import (
    ApplicationResources,
    start_application_resources,
    stop_application_resources,
)
from src.shared.application.service_registry import (
    attach_domain_services,
    build_domain_service_registry,
)
from src.shared.application.modules import register_module_dependencies
from src.shared.event_bus import EventCallback, InMemoryEventBus
from src.shared.events.domain_events import MediaUploaded, TextContentReady
from src.shared.exceptions.api_errors import register_exception_handlers
# from src.shared.monitoring.metrics_collector import metrics_collector  # Disabled due to psutil dependency
from src.shared.infrastructure.cache import cache
from src.shared.infrastructure.database import Base, engine, AsyncSessionLocal
from src.shared.infrastructure.logging_config import configure_logging, get_logger
from src.shared.infrastructure.tracing import configure_tracer
from src.shared.middleware.performance_middleware import register_performance_middleware
from src.shared.middleware.validation_middleware import register_validation_middleware
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.summarization.bootstrap import (
    create_summarization_container,
    build_summarization_module,
)
try:  # noqa: SIM105 - tolerate partial availability
    from src.text_processing.bootstrap import build_text_processing_module
except Exception as _text_processing_import_error:  # pragma: no cover - fallback path
    build_text_processing_module = None  # type: ignore[assignment]
else:
    _text_processing_import_error = None
try:  # noqa: SIM105 - optional module during refactor
    from src.topic_modeling.bootstrap import build_topic_modeling_module
except Exception:  # pragma: no cover
    build_topic_modeling_module = None  # type: ignore[assignment]
from src.transcription.bootstrap import (
    create_transcription_container,
    build_transcription_module,
)
from src.user_management.bootstrap import build_user_management_module
from src.video_processing.bootstrap import build_video_processing_module

# Ensure Celery app is importable during API startup
try:  # noqa: SIM105 - best-effort import
    from src.celery_app import celery as _celery_app  # type: ignore F401
except Exception:
    _celery_app = None  # Celery not required for API process to start

# API Routers
from src.auth.api.routers import router as auth_router

from src.monitoring.api.routers import router as monitoring_router
from src.notifications.api.routers import router as notification_router
from src.providers.api.routers import router as providers_router
try:  # noqa: SIM105 - optional router during refactor
    from src.summarization.api.routers import router as summary_router
except Exception:  # pragma: no cover
    summary_router = None
from src.transcription.api.routers import router as transcription_router
from src.media_management.api.routers import router as media_router
try:  # noqa: SIM105 - optional router during refactor
    from src.sentiment_analysis.api.routers import router as sentiment_router
except Exception:  # pragma: no cover
    sentiment_router = None
try:  # noqa: SIM105 - optional router during refactor
    from src.topic_modeling.api.routers import router as topic_modeling_router
except Exception:  # pragma: no cover
    topic_modeling_router = None
from src.admin.api.routers import router as admin_router


async def _noop_media_uploaded_handler(event: MediaUploaded) -> None:
    """Stage A placeholder handler – will be replaced in later stages."""
    _ = event  # explicit ignore until real orchestration is implemented


async def _noop_text_ready_handler(event: TextContentReady) -> None:
    """Stage A placeholder handler – will be replaced in later stages."""
    _ = event


def register_event_handlers(event_bus: InMemoryEventBus) -> None:
    """Wire placeholder handlers so smoke tests can assert registration."""

    event_bus.subscribe(MediaUploaded, _noop_media_uploaded_handler)
    event_bus.subscribe(TextContentReady, _noop_text_ready_handler)


def build_event_bus() -> InMemoryEventBus:
    """Factory for the default application event bus."""

    bus = InMemoryEventBus()
    register_event_handlers(bus)
    return bus


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configurar logging estruturado
    event_bus = build_event_bus()
    app.state.event_bus = event_bus

    lightweight_mode = os.getenv("LIGHTWEIGHT_BOOTSTRAP", "0") == "1"

    configure_logging("video-summarizer-api", level="INFO", debug_mode=True)
    logger = get_logger("main")

    # Configurar tracing
    configure_tracer("video-summarizer-api")

    logger.info("Iniciando aplicação", component="lifespan")
    logger.info("Criando tabelas do banco de dados", component="database")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - bootstrap fallback for missing types
        logger.warning(
            "database.metadata.create_all_failed",
            error=str(exc),
        )

    logger.info("Inicializando módulos e compondo aplicação", component="bootstrap")
    async with AsyncSessionLocal() as session:
        storage_factory = StorageServiceFactory()
        auth_module = build_user_management_module(session)
        monitoring_module = build_monitoring_module(session)

        media_module, media_admin_context = build_media_components(
            session=session,
            storage_service_factory=storage_factory,
            metrics_service=monitoring_module.metrics_service,
        )

        if not lightweight_mode and build_video_processing_module is not None:
            video_module = await build_video_processing_module(session)
        else:
            video_module = SimpleNamespace(service=None)

        if build_text_processing_module is not None and not lightweight_mode:
            text_module = await build_text_processing_module(session)
        else:
            logger.warning(
                "text_processing.bootstrap_unavailable",
                error=str(_text_processing_import_error) if _text_processing_import_error else None,
            )
            text_module = SimpleNamespace(service=None, task_scheduler=None)

        transcription_container = create_transcription_container(session)
        transcription_module = await build_transcription_module(
            transcription_container,
            media_queries=media_module.queries,
        )

        if not lightweight_mode:
            notification_module = await build_notification_module(
                session=session,
                auth_queries=auth_module.auth_queries,
            )
        else:
            logger.warning("notifications.bootstrap_skipped", reason="lightweight_mode")
            notification_module = SimpleNamespace(service=None, queries=None)

        if not lightweight_mode:
            try:
                summarization_container = create_summarization_container(session=session)
                summarization_module = await build_summarization_module(summarization_container)
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "summarization.bootstrap_unavailable",
                    error=str(exc),
                )
                summarization_module = SimpleNamespace(service=None)
        else:
            logger.warning("summarization.bootstrap_skipped", reason="lightweight_mode")
            summarization_module = SimpleNamespace(service=None)

        if not lightweight_mode:
            providers_module = build_providers_module()
        else:
            providers_module = SimpleNamespace(provider_registry=None)

        if build_sentiment_analysis_module is not None and not lightweight_mode:
            sentiment_module = await build_sentiment_analysis_module(
                session=session,
                transcription_queries=transcription_module.queries,
                connection_manager=manager,
                metrics_service=monitoring_module.metrics_service,
            )
        else:
            if _sentiment_import_error:
                logger.warning(
                    "sentiment_analysis.bootstrap_unavailable",
                    error=str(_sentiment_import_error),
                )
            elif lightweight_mode:
                logger.warning("sentiment_analysis.bootstrap_skipped", reason="lightweight_mode")
            sentiment_module = SimpleNamespace(service=None, repository=None)
        if build_topic_modeling_module is not None and not lightweight_mode:
            topic_module = await build_topic_modeling_module(
                session=session,
                media_queries=media_module.queries,
                transcription_queries=transcription_module.queries,
            )
        else:
            if build_topic_modeling_module is None:
                logger.warning("topic_modeling.bootstrap_unavailable")
            else:
                logger.warning("topic_modeling.bootstrap_skipped", reason="lightweight_mode")
            topic_module = SimpleNamespace(service=None, repository=None)
        admin_module = build_admin_module(
            session=session,
            auth_queries=auth_module.auth_queries,
            media_queries=media_admin_context.queries,
            delete_media_handler=media_admin_context.delete_media_handler,
            reprocess_media_handler=media_admin_context.reprocess_media_handler,
        )

        register_module_dependencies(
            app,
            auth=auth_module,
            monitoring=monitoring_module,
            media=media_module,
            transcription=transcription_module,
            notifications=notification_module,
            summarization=summarization_module,
            providers=providers_module,
            sentiment_analysis=sentiment_module,
            topic_modeling=topic_module,
            admin=admin_module,
        )
        domain_registry = build_domain_service_registry(
            user_management=auth_module,
            media_management=media_module,
        )
        attach_domain_services(app, domain_registry)
        resources = ApplicationResources(cache=cache, event_bus=event_bus)

        logger.info("Inicializando recursos compartilhados", component="bootstrap")
        try:
            await start_application_resources(resources)
        except Exception as exc:  # pragma: no cover - ignore infrastructure missing
            logger.warning("application_resources.start_failed", error=str(exc))

        logger.info("Aplicação iniciada com sucesso", component="startup")
        try:
            yield
        finally:
            logger.info("Finalizando recursos", component="shutdown")
            try:
                await stop_application_resources(resources)
            except Exception as exc:  # pragma: no cover
                logger.warning("application_resources.stop_failed", error=str(exc))
            await engine.dispose()
            logger.info("Aplicação finalizada", component="shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Media Processing API",
        description="API for uploading, transcribing, and summarizing media files (video, audio, text)",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Instrumentação OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)

    # Registrar handlers de exceção globais
    register_exception_handlers(app)

    # Registrar middlewares de validação e segurança
    register_validation_middleware(app)

    # Registrar middlewares de performance
    register_performance_middleware(app)

    # Add CORS middleware (configuração segura)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:5174",  # Vite às vezes usa esta porta
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "https://yourdomain.com"  # Adicionar domínio de produção
        ],
        allow_credentials=True,  # Necessário para cookies httpOnly
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",  # Permitir header CSRF
            "X-Requested-With"
        ],
        expose_headers=["X-CSRF-Token"],  # Expor CSRF token para frontend
    )

    # --- Route Registration ---
    app.include_router(providers_router)
    app.include_router(auth_router)
    app.include_router(media_router)
    app.include_router(transcription_router)
    if summary_router is not None:
        app.include_router(summary_router)
    if sentiment_router is not None:
        app.include_router(sentiment_router)
    if topic_modeling_router is not None:
        app.include_router(topic_modeling_router)
    app.include_router(notification_router)
    app.include_router(admin_router)
    app.include_router(monitoring_router)

    return app


app = create_app()


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Media Processing API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Endpoint para verificação de saúde da aplicação."""
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        try:
            await cache.get("health_check")
            cache_status = "connected"
        except Exception:
            cache_status = "disconnected"

        return {
            "status": "healthy",
            "database": "connected",
            "cache": cache_status,
        }
    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "cache": "unknown",
        }


@app.get("/metrics")
async def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

import os
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# OpenTelemetry Imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.admin.bootstrap import build_admin_module
from src.media_management.bootstrap import build_media_components
from src.monitoring.bootstrap import build_monitoring_module
from src.notifications.bootstrap import build_notification_module
from src.providers.bootstrap import build_providers_module
from src.shared.application.lifecycle import (
    ApplicationResources,
    start_application_resources,
    stop_application_resources,
)
from src.shared.application.modules import register_module_dependencies
from src.shared.application.service_registry import (
    attach_domain_services,
    build_domain_service_registry,
)
from src.shared.event_bus import InMemoryEventBus
from src.shared.events.domain_events import (
    MediaUploaded,
    NotificationRequested,
    TextContentReady,
)
from src.shared.exceptions.api_errors import register_exception_handlers

# from src.shared.monitoring.metrics_collector import metrics_collector  # Disabled due to psutil dependency
from src.shared.infrastructure.cache import cache
from src.shared.infrastructure.database import AsyncSessionLocal, Base, engine
from src.shared.infrastructure.logging_config import configure_logging, get_logger
from src.shared.infrastructure.tracing import configure_tracer
from src.shared.middleware.performance_middleware import register_performance_middleware
from src.shared.middleware.validation_middleware import register_validation_middleware
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.text_analysis.application.event_handlers import (
    build_text_content_ready_handler,
)
from src.text_analysis.bootstrap import build_text_analysis_module

try:  # noqa: SIM105 - tolerate partial availability during consolidation
    from src.text_analysis.api.routers import router as text_analysis_router
except Exception:  # pragma: no cover - optional module
    text_analysis_router = None  # type: ignore[assignment]
from src.notifications.application.event_handlers import handle_notification_requested
from src.user_management.bootstrap import build_user_management_module

# Ensure Celery app is importable during API startup
try:  # noqa: SIM105 - best-effort import
    from src.celery_app import celery as _celery_app  # type: ignore F401
except Exception:
    _celery_app = None  # Celery not required for API process to start

# API Routers
from src.admin.api.routers import router as admin_router
from src.media_management.api.routers import router as media_router
from src.media_processing.transcription.api.routers import (
    router as transcription_router,
)
from src.monitoring.api.routers import router as monitoring_router
from src.notifications.api.routers import router as notification_router
from src.providers.api.routers import router as providers_router
from src.user_management.api.routers import router as auth_router


def build_event_bus() -> InMemoryEventBus:
    """Factory for the default application event bus."""
    return InMemoryEventBus()


def register_domain_event_handlers(
    event_bus: InMemoryEventBus,
    *,
    media_processing_service,
    text_analysis_service=None,
) -> None:
    """Attach domain event handlers to the bus."""
    event_bus.subscribe(MediaUploaded, media_processing_service.handle_media_uploaded)
    event_bus.subscribe(TextContentReady, media_processing_service.handle_text_content_ready)
    if text_analysis_service is not None:
        event_bus.subscribe(
            TextContentReady,
            build_text_content_ready_handler(text_analysis_service),
        )
    event_bus.subscribe(NotificationRequested, handle_notification_requested)


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
        providers_module = build_providers_module()
        notification_module = build_notification_module(
            session=session,
            auth_queries=auth_module.auth_queries,
        )

        media_module, media_admin_context = build_media_components(
            session=session,
            storage_service_factory=storage_factory,
            metrics_service=monitoring_module.metrics_service,
            event_bus=event_bus,
            emit_legacy_media_task=not lightweight_mode,
        )

        if not lightweight_mode:
            text_analysis_module = build_text_analysis_module(
                session,
                media_module=media_module,
                notification_module=notification_module,
                monitoring_module=monitoring_module,
            )
        else:
            logger.warning("text_analysis.bootstrap_skipped", reason="lightweight_mode")
            text_analysis_module = SimpleNamespace(service=None)

        admin_module = build_admin_module(
            session=session,
            auth_queries=auth_module.auth_queries,
            media_queries=media_admin_context.queries,
            media_facade=media_admin_context.facade,
        )

        register_module_dependencies(
            app,
            auth=auth_module,
            monitoring=monitoring_module,
            media=media_module,
            notifications=notification_module,
            providers=providers_module,
            text_analysis=text_analysis_module,
            admin=admin_module,
        )
        domain_registry = build_domain_service_registry(
            user_management=auth_module,
            media_management=media_module,
            text_analysis=text_analysis_module,
        )
        attach_domain_services(app, domain_registry)
        resources = ApplicationResources(cache=cache, event_bus=event_bus)

        register_domain_event_handlers(
            event_bus,
            media_processing_service=media_module.processing_service,
            text_analysis_service=getattr(text_analysis_module, "service", None),
        )

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
    if text_analysis_router is not None:
        app.include_router(text_analysis_router)
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

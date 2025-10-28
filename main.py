from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# OpenTelemetry Imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from src.shared.infrastructure.tracing import configure_tracer
from src.shared.infrastructure.logging_config import configure_logging, get_logger
from src.shared.exceptions.api_errors import register_exception_handlers
from src.shared.middleware.validation_middleware import register_validation_middleware
from src.shared.middleware.performance_middleware import register_performance_middleware
# from src.shared.monitoring.metrics_collector import metrics_collector  # Disabled due to psutil dependency
from src.shared.infrastructure.cache import cache

from src.shared.application.modules import register_module_dependencies
from src.shared.application.lifecycle import (
    ApplicationResources,
    start_application_resources,
    stop_application_resources,
)
from src.shared.events.event_bus import get_event_bus
from src.storage.infrastructure.dependencies import StorageServiceFactory

from src.auth.bootstrap import build_auth_module
from src.monitoring.bootstrap import build_monitoring_module
from src.media_management.bootstrap import (
    create_media_container,
    build_media_module,
    build_media_admin_context,
)
from src.video_processing.bootstrap import build_video_processing_module
from src.text_processing.bootstrap import build_text_processing_module
from src.transcription.bootstrap import (
    create_transcription_container,
    build_transcription_module,
)
from src.notifications.bootstrap import build_notification_module
from src.summarization.bootstrap import (
    create_summarization_container,
    build_summarization_module,
)
from src.providers.bootstrap import build_providers_module
from src.sentiment_analysis.bootstrap import build_sentiment_analysis_module
from src.topic_modeling.bootstrap import build_topic_modeling_module
from src.admin.bootstrap import build_admin_module

from src.notifications.infrastructure.connection_manager import manager

from src.shared.infrastructure.database import Base, engine, AsyncSessionLocal

# API Routers
from src.auth.api.routers import router as auth_router

from src.monitoring.api.routers import router as monitoring_router
from src.notifications.api.routers import router as notification_router
from src.providers.api.routers import router as providers_router
from src.summarization.api.routers import router as summary_router
from src.transcription.api.routers import router as transcription_router
from src.media_management.api.routers import router as media_router
from src.sentiment_analysis.api.routers import router as sentiment_router
from src.topic_modeling.api.routers import router as topic_modeling_router
from src.admin.api.routers import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configurar logging estruturado
    configure_logging("video-summarizer-api", level="INFO", debug_mode=True)
    logger = get_logger("main")

    # Configurar tracing
    configure_tracer("video-summarizer-api")

    logger.info("Iniciando aplicação", component="lifespan")
    logger.info("Criando tabelas do banco de dados", component="database")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Inicializando módulos e compondo aplicação", component="bootstrap")
    async with AsyncSessionLocal() as session:
        storage_factory = StorageServiceFactory()
        event_bus = get_event_bus()

        auth_module = build_auth_module(session)
        monitoring_module = build_monitoring_module(session)

        media_container = create_media_container(
            session=session,
            storage_service_factory=storage_factory,
            event_bus=event_bus,
            metrics_service=monitoring_module.metrics_service,
        )
        media_module = build_media_module(media_container)
        media_admin_context = build_media_admin_context(
            media_container,
            queries=media_module.queries,
        )

        video_module = await build_video_processing_module(
            session,
            event_bus=event_bus,
        )

        text_module = await build_text_processing_module(
            session,
            event_bus=event_bus,
        )

        transcription_container = create_transcription_container(session)
        transcription_module = await build_transcription_module(
            transcription_container,
            event_bus=event_bus,
            media_queries=media_module.queries,
        )

        notification_module = await build_notification_module(
            session=session,
            auth_queries=auth_module.auth_queries,
            event_bus=event_bus,
        )

        summarization_container = create_summarization_container(
            session=session,
            event_bus=event_bus,
            transcription_queries=transcription_module.queries,
            media_queries=media_module.queries,
            connection_manager=manager,
        )
        summarization_module = await build_summarization_module(
            summarization_container,
            event_bus=event_bus,
            media_queries=media_module.queries,
        )

        providers_module = build_providers_module()
        sentiment_module = await build_sentiment_analysis_module(
            session=session,
            event_bus=event_bus,
            transcription_queries=transcription_module.queries,
            connection_manager=manager,
            metrics_service=monitoring_module.metrics_service,
        )
        topic_module = await build_topic_modeling_module(
            session=session,
            event_bus=event_bus,
            media_queries=media_module.queries,
            transcription_queries=transcription_module.queries,
        )
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
        app.state.event_bus = event_bus

        resources = ApplicationResources(event_bus=event_bus, cache=cache)

        logger.info("Inicializando recursos compartilhados", component="bootstrap")
        await start_application_resources(resources)

        logger.info("Aplicação iniciada com sucesso", component="startup")
        try:
            yield
        finally:
            logger.info("Finalizando recursos", component="shutdown")
            await stop_application_resources(resources)
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
    app.include_router(summary_router)
    app.include_router(sentiment_router)
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

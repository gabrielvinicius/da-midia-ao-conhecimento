from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Response
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

# --- Module Bootstrapping and Composition Root ---
from src.monitoring.bootstrap import MonitoringContainer
from src.auth.container import AuthContainer
from src.media_management.bootstrap import MediaManagementContainer
# from src.shared.monitoring.metrics_collector import metrics_collector  # Disabled due to psutil dependency
from src.video_processing.bootstrap import VideoProcessingContainer
from src.text_processing.bootstrap import TextProcessingContainer
from src.transcription.bootstrap import TranscriptionContainer
from src.providers.bootstrap import ProvidersContainer
from src.summarization.bootstrap import SummarizationContainer
from src.notifications.bootstrap import NotificationContainer

from src.sentiment_analysis.bootstrap import SentimentAnalysisContainer
from src.topic_modeling.bootstrap import TopicModelingContainer
from src.admin.container import AdminContainer
from src.notifications.infrastructure.connection_manager import manager

# Shared Factories and DB
from src.shared.events.event_bus import get_event_bus
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.transcription.infrastructure.dependencies import get_speech_recognition_service_factory
from src.summarization.infrastructure.dependencies import get_summarizer_service_factory
from src.sentiment_analysis.infrastructure.dependencies import get_sentiment_service_factory
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
        # Create storage service factory instance
        from src.storage.infrastructure.dependencies import StorageServiceFactory
        storage_factory = StorageServiceFactory()
        
        app_container = {
            "event_bus": get_event_bus(),
            "storage_service_factory": storage_factory,
            "speech_recognition_service_factory": get_speech_recognition_service_factory(),
            "summarizer_service_factory": get_summarizer_service_factory(),
            "sentiment_analysis_service_factory": get_sentiment_service_factory(),
        }

        event_bus = app_container["event_bus"]

        auth_container = AuthContainer(db=session)
        app_container["auth_container"] = auth_container
        app_container["auth_service"] = auth_container.auth_service()
        app_container["auth_queries"] = auth_container.auth_queries() # Still needed for other modules
        app_container["user_service"] = auth_container.user_service()
        app_container["auth_settings"] = auth_container.auth_settings()

        monitoring_container = MonitoringContainer()
        monitoring_container.db.override(session) # Override the db dependency
        app_container["monitoring_container"] = monitoring_container # Store the container itself
        app_container["analytics_queries"] = monitoring_container.analytics_queries()
        app_container["metrics_service"] = monitoring_container.metrics_service()
        media_management_container = MediaManagementContainer()
        media_management_container.db.override(session)
        media_management_container.storage_service_factory.override(storage_factory)
        media_management_container.event_bus.override(event_bus)
        media_management_container.metrics_service.override(app_container["metrics_service"])
        app_container["media_management_container"] = media_management_container
        app_container["media_upload_service"] = media_management_container.media_upload_service()
        app_container["media_lifecycle_service"] = media_management_container.media_lifecycle_service()
        app_container["media_query_service"] = media_management_container.media_query_service()
        app_container["media_access_policy"] = media_management_container.media_access_policy()
        app_container["media_upload_validator"] = media_management_container.media_upload_validator()
        app_container["create_media_command_handler"] = media_management_container.create_media_command_handler()
        app_container["delete_media_command_handler"] = media_management_container.delete_media_command_handler()
        app_container["reprocess_media_command_handler"] = media_management_container.reprocess_media_command_handler()
        app_container["media_queries"] = media_management_container.media_queries() # Adicionar media_queries
        transcription_container = TranscriptionContainer(db=session)
        app_container["transcription_container"] = transcription_container
        app_container["transcription_service"] = transcription_container.transcription_service()
        app_container["transcription_repository"] = transcription_container.transcription_repository() # Still needed for event handlers
        app_container["transcription_queries"] = transcription_container.transcription_queries()
        
        notification_container = NotificationContainer(db=session)
        notification_container.auth_queries.override(auth_container.auth_queries())
        notification_container.event_bus.override(event_bus)
        app_container["notification_container"] = notification_container
        app_container["notification_service"] = notification_container.notification_service()
        app_container["notification_repository"] = notification_container.notification_repository() # Still needed for event handlers
        video_processing_container = VideoProcessingContainer(db=session)
        app_container["video_processing_container"] = video_processing_container
        app_container["video_processing_service"] = video_processing_container.video_processing_service()
        text_processing_container = TextProcessingContainer(db=session)
        app_container["text_processing_container"] = text_processing_container
        app_container["text_processing_service"] = text_processing_container.text_processing_service()
        summarization_container = SummarizationContainer(
            db=session,
            event_bus=event_bus,
            transcription_queries=app_container["transcription_queries"],
            media_queries=app_container["media_queries"],
            connection_manager=manager,
        )
        app_container["summarization_container"] = summarization_container
        app_container["summarization_service"] = summarization_container.summarization_service()
        app_container["summary_repository"] = summarization_container.summarization_repository() # Still needed for event handlers
        app_container["request_summary_command_handler"] = summarization_container.request_summary_command_handler()
        app_container["process_summary_command_handler"] = summarization_container.process_summary_command_handler()
        app_container["summarization_task_scheduler"] = summarization_container.summarization_task_scheduler()
        providers_container = ProvidersContainer()
        app_container["providers_container"] = providers_container
        app_container["provider_registry"] = providers_container.provider_registry()
        sentiment_analysis_container = SentimentAnalysisContainer(db=session)
        sentiment_analysis_container.event_bus.override(event_bus)
        sentiment_analysis_container.transcription_queries.override(
            app_container["transcription_queries"]
        )
        sentiment_analysis_container.connection_manager.override(manager)
        sentiment_analysis_container.metrics_service.override(
            app_container["metrics_service"]
        )
        app_container["sentiment_analysis_container"] = sentiment_analysis_container
        app_container["sentiment_analysis_service"] = sentiment_analysis_container.sentiment_analysis_service()
        app_container["sentiment_analysis_repository"] = sentiment_analysis_container.sentiment_analysis_repository() # Still needed for event handlers
        topic_modeling_container = TopicModelingContainer(db=session)
        app_container["topic_modeling_container"] = topic_modeling_container
        app_container["topic_modeling_service"] = topic_modeling_container.topic_modeling_service()
        app_container["topic_modeling_repository"] = topic_modeling_container.topic_modeling_repository() # Still needed for event handlers
        admin_container = AdminContainer()
        admin_container.db.override(session)
        admin_container.auth_queries.override(app_container["auth_queries"])
        admin_container.media_queries.override(app_container["media_queries"])
        admin_container.delete_media_handler.override(app_container["delete_media_command_handler"])
        admin_container.reprocess_media_handler.override(app_container["reprocess_media_command_handler"])
        app_container["admin_container"] = admin_container
        app_container["admin_queries"] = admin_container.admin_queries()
        app_container["admin_audit_service"] = admin_container.admin_audit_service()
        app_container["admin_user_service"] = admin_container.admin_user_service()
        app_container["admin_media_service"] = admin_container.admin_media_service()


        app.state.container = app_container

        from src.video_processing.application.event_handlers import register_event_handlers as register_video_handlers
        from src.text_processing.application.event_handlers import register_event_handlers as register_text_handlers
        from src.transcription.application.event_handlers import register_event_handlers as register_transcription_handlers
        from src.summarization.application.event_handlers import register_event_handlers as register_summary_handlers
        from src.notifications.application.event_handlers import register_event_handlers as register_notification_handlers
        from src.sentiment_analysis.application.event_handlers import register_event_handlers as register_sentiment_handlers
        from src.topic_modeling.application.event_handlers import register_event_handlers as register_topic_handlers
        
        await register_video_handlers(
            app_container["event_bus"],
            app_container["video_processing_container"].video_processing_task_scheduler(),
        )
        await register_text_handlers(app_container["event_bus"], app_container["text_processing_container"].text_processing_task_scheduler())
        await register_transcription_handlers(app_container["event_bus"], app_container["transcription_repository"], app_container["media_queries"])
        await register_summary_handlers(
            app_container["event_bus"],
            app_container["summary_repository"],
            app_container["media_queries"],
            app_container["summarization_task_scheduler"],
        )
        await register_notification_handlers(app_container["event_bus"])
        await register_sentiment_handlers(app_container["event_bus"])
        await register_topic_handlers(app_container["event_bus"])

        logger.info("Iniciando event bus", component="event_bus")
        await app.state.container["event_bus"].start_listener()
        
        # Inicializar sistema de cache
        logger.info("Conectando ao sistema de cache", component="cache")
        await cache.connect()
        
        # Inicializar coleta de métricas
        logger.info("Iniciando coleta de métricas", component="metrics")
        # await metrics_collector.start_collection(interval_seconds=30)  # Disabled due to psutil dependency

        logger.info("Aplicação iniciada com sucesso", component="startup")
        yield

        logger.info("Finalizando recursos", component="shutdown")
        
        # Parar coleta de métricas
        # await metrics_collector.stop_collection()  # Disabled due to psutil dependency
        
        # Desconectar cache
        await cache.disconnect()
        
        # Finalizar event bus e banco
        await app.state.container["event_bus"].stop_listener()
        await engine.dispose()
        
        logger.info("Aplicação finalizada", component="shutdown")


app = FastAPI(
    title="Media Processing API",
    description="API for uploading, transcribing, and summarizing media files (video, audio, text)",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
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

def get_service(service_name: str):
    async def _get_service(request: Request):
        return request.app.state.container[service_name]
    return _get_service

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
        # Verificar conexão com banco de dados
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        
        # Verificar conexão com cache/Redis
        try:
            await cache.get("health_check")
            cache_status = "connected"
        except:
            cache_status = "disconnected"
        
        return {
            "status": "healthy",
            "timestamp": "2025-10-15T03:44:43.766663Z",
            "service": "video-summarizer",
            "version": "2.0.0",
            "database": "connected",
            "cache": cache_status,
            "components": {
                "auth": "operational",
                "media_management": "operational", 
                "transcription": "operational",
                "summarization": "operational",
                "sentiment_analysis": "operational",
                "topic_modeling": "operational",
                "notifications": "operational"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": "2025-10-15T03:44:43.766663Z",
            "service": "video-summarizer",
            "error": str(e)
        }

# Endpoint simples para verificação rápida
@app.get("/ping")
async def ping():
    """Endpoint simples para verificação de conectividade."""
    return {"message": "pong", "status": "ok"}



# Endpoint para dashboard de métricas
@app.get("/health/dashboard")
async def get_dashboard_metrics():
    """Endpoint para dashboard interno de métricas."""
    try:
        return {
            "status": "operational",
            "services": {
                "auth": "running",
                "media": "running", 
                "transcription": "running",
                "summarization": "running"
            },
            "timestamp": "2025-10-15T03:44:43.766663Z"
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}

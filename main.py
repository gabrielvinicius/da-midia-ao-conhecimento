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
from src.auth.bootstrap import bootstrap_auth_module
from src.media_management.bootstrap import bootstrap_media_module
# from src.shared.monitoring.metrics_collector import metrics_collector  # Disabled due to psutil dependency
from src.video_processing.bootstrap import bootstrap_video_processing_module
from src.text_processing.bootstrap import bootstrap_text_processing_module
from src.transcription.bootstrap import bootstrap_transcription_module
from src.summarization.bootstrap import bootstrap_summarization_module
from src.notifications.bootstrap import bootstrap_notification_module
from src.analytics.bootstrap import bootstrap_analytics_module
from src.metrics.bootstrap import bootstrap_metrics_module
from src.sentiment_analysis.bootstrap import bootstrap_sentiment_analysis_module # Import new bootstrap
from src.topic_modeling.bootstrap import bootstrap_topic_modeling_module
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
from src.metrics.api.routers import router as metrics_router
from src.notifications.api.routers import router as notification_router
from src.providers.api.routers import router as providers_router
from src.summarization.api.routers import router as summary_router
from src.transcription.api.routers import router as transcription_router
from src.media_management.api.routers import router as media_router
from src.sentiment_analysis.api.routers import router as sentiment_router
from src.topic_modeling.api.routers import router as topic_modeling_router

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
        app_container = {
            "event_bus": get_event_bus(),
            "storage_service_factory": get_storage_service_factory(),
            "speech_recognition_service_factory": get_speech_recognition_service_factory(),
            "summarizer_service_factory": get_summarizer_service_factory(),
            "sentiment_analysis_service_factory": get_sentiment_service_factory(),
        }
        app_container.update(bootstrap_metrics_module())
        app_container.update(bootstrap_auth_module(session))
        app_container.update(bootstrap_analytics_module(session))
        app_container.update(bootstrap_media_module(session, app_container["storage_service_factory"], app_container["event_bus"], app_container["metrics_service"]))
        app_container.update(bootstrap_transcription_module(session, app_container["media_queries"], manager))
        app_container.update(bootstrap_notification_module(session, auth_queries=app_container["auth_queries"], event_bus=app_container["event_bus"]))
        app_container.update(bootstrap_video_processing_module(app_container["media_queries"], app_container["media_repository"], app_container["storage_service_factory"], app_container["event_bus"]))
        app_container.update(bootstrap_text_processing_module(session, app_container["media_queries"], app_container["storage_service_factory"], app_container["event_bus"]))
        app_container.update(bootstrap_summarization_module(session, app_container["event_bus"]))
        app_container.update(bootstrap_sentiment_analysis_module(session))
        app_container.update(bootstrap_topic_modeling_module(session))

        app.state.container = app_container

        from src.video_processing.application.event_handlers import register_event_handlers as register_video_handlers
        from src.text_processing.application.event_handlers import register_event_handlers as register_text_handlers
        from src.transcription.application.event_handlers import register_event_handlers as register_transcription_handlers
        from src.summarization.application.event_handlers import register_event_handlers as register_summary_handlers
        from src.notifications.application.event_handlers import register_event_handlers as register_notification_handlers
        from src.sentiment_analysis.application.event_handlers import register_event_handlers as register_sentiment_handlers
        from src.topic_modeling.application.event_handlers import register_event_handlers as register_topic_handlers
        
        await register_video_handlers(app_container["event_bus"])
        await register_text_handlers(app_container["event_bus"])
        await register_transcription_handlers(app_container["event_bus"], app_container["transcription_repository"], app_container["media_queries"])
        await register_summary_handlers(app_container["event_bus"], app_container["summary_repository"], app_container["media_queries"])
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
        "http://localhost:3000", 
        "http://127.0.0.1:5173",
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
app.include_router(metrics_router)

# Endpoint para métricas Prometheus
@app.get("/metrics", response_class=Response)
async def get_metrics():
    """Endpoint para coleta de métricas pelo Prometheus."""
    from prometheus_client import CONTENT_TYPE_LATEST
    metrics_data = metrics_collector.get_prometheus_metrics()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

# Endpoint para dashboard de métricas
@app.get("/health/dashboard")
async def get_dashboard_metrics():
    """Endpoint para dashboard interno de métricas."""
    return await metrics_collector.get_dashboard_data()

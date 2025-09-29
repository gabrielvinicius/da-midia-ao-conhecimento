from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# OpenTelemetry Imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from src.shared.infrastructure.tracing import configure_tracer

# --- Module Bootstrapping and Composition Root ---
from src.auth.bootstrap import bootstrap_auth_module
from src.media_management.bootstrap import bootstrap_media_module
from src.transcription.bootstrap import bootstrap_transcription_module
from src.summarization.bootstrap import bootstrap_summarization_module
from src.notifications.bootstrap import bootstrap_notification_module
from src.analytics.bootstrap import bootstrap_analytics_module
from src.metrics.bootstrap import bootstrap_metrics_module

# Shared Factories and DB
from src.shared.events.event_bus import get_event_bus
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.transcription.infrastructure.dependencies import get_speech_recognition_service_factory
from src.summarization.infrastructure.dependencies import get_summarizer_service_factory
from src.shared.infrastructure.database import Base, engine, AsyncSessionLocal

# API Routers
from src.auth.api.routers import router as auth_router
from src.metrics.api.routers import router as metrics_router
from src.notifications.api.routers import router as notification_router
from src.providers.api.routers import router as providers_router
from src.summarization.api.routers import router as summary_router
from src.transcription.api.routers import router as transcription_router
from src.media_management.api.routers import router as media_router # The one true entry point


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Configure Observability
    configure_tracer("video-summarizer-api")

    # 2. Initialize Database
    print("⏳ Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 3. Initialize Modules and Compose Application (Composition Root)
    print("⚙️ Initializing modules and composing application...")
    async with AsyncSessionLocal() as session:
        # Create shared components and factories first
        event_bus = get_event_bus()
        storage_factory = get_storage_service_factory()
        speech_factory = get_speech_recognition_service_factory()
        summarizer_factory = get_summarizer_service_factory()
        metrics_components = bootstrap_metrics_module()

        # Bootstrap all modules, passing dependencies explicitly
        auth_components = bootstrap_auth_module(session)
        analytics_components = bootstrap_analytics_module(session)
        transcription_components = bootstrap_transcription_module(session)
        media_components = bootstrap_media_module(session, storage_factory, event_bus)
        notification_components = bootstrap_notification_module(session, user_repository=auth_components["user_repository"])
        summarization_components = bootstrap_summarization_module(session, event_bus, transcription_queries=transcription_components["transcription_queries"])

        # Create a unified container dictionary for the application state
        app.state.container = {
            "event_bus": event_bus,
            "storage_service_factory": storage_factory,
            "speech_recognition_service_factory": speech_factory,
            "summarizer_service_factory": summarizer_factory,
            **metrics_components,
            **auth_components,
            **analytics_components,
            **transcription_components,
            **notification_components,
            **media_components,
            **summarization_components,
        }

        # 4. Start Background Services
        print("🚀 Starting event bus...")
        await app.state.container["event_bus"].start_listener()

        yield

        # 5. Clean up resources
        print("🛑 Shutting down resources...")
        await app.state.container["event_bus"].stop_listener()
        await engine.dispose()


app = FastAPI(
    title="Media Processing API",
    description="API for uploading, transcribing, and summarizing media files (video, audio, text)",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

FastAPIInstrumentor.instrument_app(app)

# --- Dependency Injection Helper ---
def get_service(service_name: str):
    async def _get_service(request: Request):
        return request.app.state.container[service_name]
    return _get_service

# --- Route Registration ---
app.include_router(providers_router)
app.include_router(auth_router)
app.include_router(media_router) # New entry point
app.include_router(transcription_router)
app.include_router(summary_router)
app.include_router(notification_router)
app.include_router(metrics_router)

import os
from contextlib import asynccontextmanager

from fastapi import (
    Depends,
    FastAPI,
    Response,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from fastapi.middleware.cors import CORSMiddleware

# OpenTelemetry Imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.shared.api.monitoring_router import router as monitoring_router
from src.shared.api.providers_router import router as providers_router
from src.shared.application.lifecycle import (
    ApplicationResources,
    start_application_resources,
    stop_application_resources,
)
from src.shared.api.modules import (
    DEFAULT_MODULE_SPECS,
    include_module_routers,
    register_module_dependencies,
)
from src.media_management.bootstrap import (
    build_media_components,
)
from src.user_management.bootstrap import (
    build_user_management_components,
)
from src.admin.bootstrap import (
    build_admin_module,
)
from src.user_management.infrastructure.dependencies.data_erasers import (
    build_user_data_erasers,
)
from src.notifications.bootstrap import (
    build_notifications_module,
)
from src.text_analysis.bootstrap import (
    build_text_analysis_module,
)
from src.shared.domain.events import (
    MediaUploaded,
)

# metrics_collector disabled (psutil dep)
from src.shared.infrastructure.caching.cache import cache
from src.shared.infrastructure.database.db import (
    AsyncSessionLocal,
    DbSessionScopeMiddleware,
    RequestScopedSession,
    Base,
    engine,
    engine_sync,
)
from src.shared.infrastructure.exceptions.exception_handlers import (
    register_exception_handlers,
)
from src.shared.infrastructure.messaging.event_bus_factory import get_event_bus
from src.shared.infrastructure.middleware.correlation_middleware import (
    CorrelationIdMiddleware,
)
from src.shared.infrastructure.middleware.performance_middleware import (
    register_performance_middleware,
)
from src.shared.infrastructure.middleware.validation_middleware import (
    register_validation_middleware,
)
from src.shared.infrastructure.observability.health.health_check import (
    router as health_router,
)
from src.shared.infrastructure.observability.logging.logging_config import (
    configure_logging,
    get_logger,
)
from src.shared.infrastructure.observability.tracing.tracer import configure_tracer
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.user_management.api.dependencies import get_current_user_websocket
from src.user_management.domain import User
from src.notifications.infrastructure.realtime.redis_pubsub_bridge import (
    RedisNotificationPubSubBridge,
)

# Ensure Celery app is importable during API startup
try:  # noqa: SIM105 - best-effort import
    from src.celery_app import celery as _celery_app  # type: ignore F401
except Exception:
    _celery_app = None  # Celery not required for API process to start


def build_event_bus():
    """Factory for the default application event bus."""
    return get_event_bus()


def register_domain_event_handlers(
    event_bus,
    *,
    storage_factory: StorageServiceFactory,
) -> None:
    """Registra handlers do pipeline no processo da API.

    Decisão arquitetural:
    - Event bus é apenas in-process (memory).
    - Integração entre processos ocorre via Celery/DB.
    - Portanto, a API assina somente o evento de entrada do pipeline
      (`MediaUploaded`) para agendar o processamento no worker.

    Motivação técnica:
    - AsyncSession não pode ser singleton (concorrência) e não deve ser
      compartilhada entre requests/eventos.
    """

    async def _handle_media_uploaded(event: MediaUploaded) -> None:
        async with AsyncSessionLocal() as session:
            from src.media_processing.infrastructure.dependencies.builders import (
                build_media_processing_event_handlers,
            )

            provider_name = getattr(event, "storage_provider", None) or "local"
            handlers = build_media_processing_event_handlers(
                session=session,
                storage_factory=storage_factory,
                event_bus=event_bus,
                storage_provider=provider_name,
            )
            await handlers.handle_media_uploaded(event)

    event_bus.subscribe(MediaUploaded, _handle_media_uploaded)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configurar logging estruturado
    event_bus = build_event_bus()
    app.state.event_bus = event_bus

    lightweight_mode = os.getenv("LIGHTWEIGHT_BOOTSTRAP", "0") == "1"

    configure_logging("video-summarizer-api", level="INFO", debug_mode=True)
    logger = get_logger("main")

    if not lightweight_mode:
        from src.user_management.config.settings import ensure_secure_secret, user_settings

        ensure_secure_secret(user_settings)

    # Configurar tracing
    configure_tracer("video-summarizer-api")

    logger.info("Iniciando aplicação", component="lifespan")
    logger.info("Criando tabelas do banco de dados", component="database")

    try:
        if lightweight_mode:
            # Em modo leve (testes unitários), cria as tabelas em memória/sqlite.
            Base.metadata.create_all(bind=engine_sync)
        else:
            # Em produção/dev com Postgres, usamos Alembic.
            # O create_all aqui impediria o Alembic de detectar mudanças.
            logger.info("Database managed by Alembic, skipping metadata.create_all", component="database")
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "database.metadata_create_all_failed",
            error=str(exc),
        )

    logger.info("Inicializando serviços compartilhados", component="bootstrap")

    storage_factory = StorageServiceFactory()

    # Read-model: catálogo de providers expostos no pipeline (sem vazar adapters internos)
    from src.media_processing.infrastructure.adapters.provider_catalog_adapter import (
        MediaProcessingProvidersCatalogAdapter,
    )
    from src.shared.application.services.providers_read_service import (
        ProvidersReadService,
    )
    from src.storage.infrastructure.adapters.provider_catalog_adapter import (
        StorageProvidersCatalogAdapter,
    )
    from src.text_analysis.infrastructure.adapters.provider_catalog_adapter import (
        TextAnalysisProvidersCatalogAdapter,
    )
    from src.notifications.infrastructure.adapters.provider_catalog_adapter import (
        NotificationProvidersCatalogAdapter,
    )

    app.state.providers_read_service = ProvidersReadService(
        catalogs=[
            StorageProvidersCatalogAdapter(storage_factory),
            MediaProcessingProvidersCatalogAdapter(),
            TextAnalysisProvidersCatalogAdapter(),
            NotificationProvidersCatalogAdapter(),
        ]
    )

    # Event handlers do pipeline (sessão por evento)
    register_domain_event_handlers(
        event_bus,
        storage_factory=storage_factory,
    )

    # --- Manually build and bind the Media Module ---
    # This is critical to ensure dependencies like storage_downloader are injected
    # instead of using the default (empty) dependencies in routes.
    # Os módulos são montados uma vez, mas cada requisição recebe a sua sessão
    # (RequestScopedSession + DbSessionScopeMiddleware); antes, a sessão aberta
    # aqui era compartilhada por todas as requisições.
    session = RequestScopedSession
    media_module, _ = build_media_components(
        session=session,
        storage_service_factory=storage_factory,
        event_bus=event_bus,
    )
    # Excluir um usuário apaga antes as mídias, os avisos e as avaliações dele.
    user_management_module = build_user_management_components(
        session=session,
        data_erasers=build_user_data_erasers(session, media_module.media_service),
    )
    
    notifications_module = build_notifications_module(session=session)

    admin_module = build_admin_module(
        session=session,
        auth_queries=user_management_module.auth_queries,
        user_service_core=user_management_module.user_service,
        media_service_core=media_module.media_service,
    )

    text_analysis_module = await build_text_analysis_module(
        session=session,
        event_bus=event_bus,
    )

    # Register all built modules so FastAPI uses the correct instances
    register_module_dependencies(
        app,
        module_instances={
            "media": media_module,
            "auth": user_management_module,
            "notifications": notifications_module,
            "admin": admin_module,
            "text_analysis": text_analysis_module,
        },
        specs=DEFAULT_MODULE_SPECS,
    )

    notifications_bridge = None
    if not lightweight_mode:
        try:
            notifications_bridge = RedisNotificationPubSubBridge()
            await notifications_bridge.start()
            app.state.notifications_bridge = notifications_bridge
        except Exception as exc:  # pragma: no cover - infraestrutura opcional
            logger.warning(
                "notifications.realtime.bridge_start_failed",
                error=str(exc),
            )
            notifications_bridge = None

    resources = ApplicationResources(cache=cache, event_bus=event_bus)

    # O primeiro administrador só é criado quando as duas variáveis são
    # definidas. Não há valor padrão: uma senha fixa no código-fonte público
    # daria acesso administrativo a qualquer instalação nova.
    default_admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "").strip()
    default_admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "")
    force_admin_password = (
        os.getenv("DEFAULT_ADMIN_FORCE_PASSWORD", "0").lower() in {"1", "true", "yes"}
    )

    if not lightweight_mode and not (default_admin_email and default_admin_password):
        logger.info(
            "auth.ensure_admin.skipped",
            reason="DEFAULT_ADMIN_EMAIL e DEFAULT_ADMIN_PASSWORD não definidos",
        )

    if not lightweight_mode and default_admin_email and default_admin_password:
        try:
            async with AsyncSessionLocal() as session:
                # A mesma montagem do módulo usada pela API.
                user_service = build_user_management_components(session=session).user_service

                admin_user = await user_service.ensure_admin_user(
                    email=default_admin_email,
                    default_password=default_admin_password,
                    force_password_reset=force_admin_password,
                )

            logger.info(
                "auth.ensure_admin.success",
                email=default_admin_email,
                user_id=str(admin_user.id),
                force_password_reset=force_admin_password,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(
                "auth.ensure_admin.failed",
                email=default_admin_email,
                error=str(exc),
            )

    if not lightweight_mode:
        logger.info("Inicializando recursos compartilhados", component="bootstrap")
        try:
            await start_application_resources(resources)
        except Exception as exc:  # pragma: no cover - ignore infrastructure missing
            logger.warning("application_resources.start_failed", error=str(exc))

    logger.info("Aplicação iniciada com sucesso", component="startup")
    try:
        yield
    finally:
        if notifications_bridge is not None:
            try:
                await notifications_bridge.stop()
            except Exception:
                pass
        logger.info("Finalizando recursos", component="shutdown")
        if not lightweight_mode:
            try:
                await stop_application_resources(resources)
            except Exception as exc:  # pragma: no cover
                logger.warning("application_resources.stop_failed", error=str(exc))
        if engine is not None:
            await engine.dispose()
        logger.info("Aplicação finalizada", component="shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Media Processing API",
        description=(
            "API for uploading, transcribing, and summarizing media files "
            "(video, audio, text)"
        ),
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Correlation ID middleware (First to run)
    app.add_middleware(CorrelationIdMiddleware)


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
            "X-Requested-With",
            "X-Correlation-ID",  # Permitir header de correlação
        ],
        expose_headers=[
            "X-CSRF-Token",
            "X-Correlation-ID",
        ],  # Expor CSRF e Correlation ID
    )

    # --- Route Registration ---
    include_module_routers(app, specs=DEFAULT_MODULE_SPECS)
    app.include_router(health_router)
    app.include_router(monitoring_router)
    app.include_router(providers_router)

    # Add WebSocket endpoints for real-time notifications
    @app.websocket("/ws/notifications")
    async def websocket_notifications(
        websocket: WebSocket,
        current_user: User = Depends(get_current_user_websocket),
    ):
        from src.notifications.infrastructure.adapters.websockets.connection_manager import (
            manager,
        )
        from src.notifications.infrastructure.repositories.notification_repository import (
            NotificationRepository,
        )
        from src.shared.infrastructure.database.db import AsyncSessionLocal

        user_id = str(current_user.id)
        try:
            await manager.connect(user_id, websocket)

            # Envia backlog de notificações ainda não entregues via realtime.
            async with AsyncSessionLocal() as session:
                repo = NotificationRepository(db=session)
                pending = await repo.list_undelivered_by_user(user_id, limit=50)
                for notif in pending:
                    ok = await manager.send_to_user(
                        user_id,
                        {
                            "notification_id": str(notif.id),
                            "type": notif.type.value,
                            "message": notif.content,
                            "priority": notif.priority.value,
                            "created_at": notif.created_at,
                            "variables": notif.variables,
                        },
                    )
                    if ok:
                        await repo.mark_as_delivered(str(notif.id))

            try:
                while True:
                    data = await websocket.receive_text()
                    print(f"Received message from user {user_id}: {data}")
                    await websocket.send_text(f"Server received: {data}")
            except WebSocketDisconnect:
                manager.disconnect(user_id, websocket)
                print(f"WebSocket connection for user {user_id} closed")
        except WebSocketException as exc:
            await websocket.close(code=exc.code, reason=exc.reason or "Unauthorized")
        except Exception as e:
            print(f"WebSocket error: {e}")
            await websocket.close(code=1000)

    # Mais externo: cada requisição ganha sua própria sessão de banco, fechada
    # ao fim (ver RequestScopedSession).
    app.add_middleware(DbSessionScopeMiddleware)

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

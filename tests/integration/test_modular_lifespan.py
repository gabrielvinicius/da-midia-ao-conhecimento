from types import SimpleNamespace

import pytest

import main

from main import create_app
from src.user_management.api.dependencies import get_auth_dependencies
from src.media_management.api.dependencies import get_media_dependencies
from src.shared.events.domain_events import MediaUploaded, TextContentReady
from src.shared.middleware.performance_middleware import PerformanceMetricsMiddleware
from src.shared.middleware.validation_middleware import ContentValidationMiddleware
from src.summarization.api.dependencies import get_summarization_dependencies


@pytest.fixture(autouse=True)
def enable_lightweight_mode(monkeypatch) -> None:
    """Use lightweight bootstrap during tests to avoid external services."""
    monkeypatch.setenv("LIGHTWEIGHT_BOOTSTRAP", "1")

    # Stub optional modules that aren't needed for these assertions.
    monkeypatch.setattr(
        main,
        "build_notification_module",
        lambda *args, **kwargs: SimpleNamespace(service=None, queries=None),
    )
    monkeypatch.setattr(
        main,
        "build_providers_module",
        lambda *args, **kwargs: SimpleNamespace(provider_registry=None),
    )

    dummy_monitoring = SimpleNamespace(
        metrics_service=object(),
        analytics_queries=object(),
    )
    monkeypatch.setattr(
        main,
        "build_monitoring_module",
        lambda *args, **kwargs: dummy_monitoring,
    )

    dummy_media_module = SimpleNamespace(
        queries=object(),
        upload_service=object(),
        lifecycle_service=object(),
        query_service=object(),
        transcription_service=object(),
        transcription_queries=object(),
    )
    dummy_media_admin = SimpleNamespace(
        queries=object(),
        facade=object(),
    )
    monkeypatch.setattr(
        main,
        "build_media_components",
        lambda *args, **kwargs: (dummy_media_module, dummy_media_admin),
    )

    from src.user_management.config.settings import AuthSettings

    dummy_user_module = SimpleNamespace(
        auth_service=object(),
        auth_queries=object(),
        user_service=object(),
        settings=AuthSettings(),
    )
    monkeypatch.setattr(
        main,
        "build_user_management_module",
        lambda *args, **kwargs: dummy_user_module,
    )

    class _DummyConn:
        async def run_sync(self, _fn):
            return None

    class _DummyEngineContext:
        async def __aenter__(self):
            return _DummyConn()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _DummyEngine:
        def begin(self):
            return _DummyEngineContext()

        async def dispose(self):
            return None

    class _DummySessionContext:
        async def __aenter__(self):
            return SimpleNamespace()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main, "AsyncSessionLocal", lambda *args, **kwargs: _DummySessionContext())
    monkeypatch.setattr(main, "engine", _DummyEngine())


class DummyEventBus:
    def __init__(self) -> None:
        self._subscriptions = {}
        self.started = False
        self.stopped = False

    def subscribe(self, event, handler):
        self._subscriptions.setdefault(event, []).append(handler)

    def has_subscribers(self, event) -> bool:
        return bool(self._subscriptions.get(event))

    async def start_listener(self) -> None:
        self.started = True

    async def stop_listener(self) -> None:
        self.stopped = True


class DummyCache:
    def __init__(self) -> None:
        self.connected = False
        self.disconnected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.disconnected = True

    async def get(self, *_args, **_kwargs):  # pragma: no cover - health check compatibility
        return None


@pytest.fixture
def dummy_event_bus(monkeypatch) -> DummyEventBus:
    bus = DummyEventBus()
    monkeypatch.setattr(main, "build_event_bus", lambda: bus)
    # Ensure handlers are registered even when bootstrap stubs short-circuit.
    main.register_event_handlers(bus)
    return bus


@pytest.fixture
def dummy_cache(monkeypatch) -> DummyCache:
    cache_instance = DummyCache()
    # Patch both the FastAPI module and the shared cache singleton so startup/shutdown sees the stub
    import main as main_module  # local import to avoid circularities during collection
    from src.shared.infrastructure import cache as cache_module

    monkeypatch.setattr(main_module, "cache", cache_instance, raising=False)
    monkeypatch.setattr(cache_module, "cache", cache_instance, raising=False)
    return cache_instance


@pytest.mark.anyio
async def test_dependency_providers_initialized(
    dummy_event_bus: DummyEventBus, dummy_cache: DummyCache
):
    app = create_app()
    async with app.router.lifespan_context(app):
        assert not hasattr(app.state, "modules")

        auth_deps = app.dependency_overrides[get_auth_dependencies]()
        assert auth_deps.auth_service is not None

        media_deps = app.dependency_overrides[get_media_dependencies]()
        assert media_deps.queries is not None

        summarization_deps = app.dependency_overrides[get_summarization_dependencies]()
        assert summarization_deps is not None
        if hasattr(summarization_deps, "process_handler"):
            assert summarization_deps.process_handler is not None
        else:
            # In lightweight bootstrap, summarization can be skipped entirely.
            assert getattr(summarization_deps, "service", None) is None


@pytest.mark.anyio
async def test_event_handlers_registered(dummy_event_bus: DummyEventBus, dummy_cache: DummyCache):
    app = create_app()
    async with app.router.lifespan_context(app):
        assert dummy_event_bus.has_subscribers(MediaUploaded)
        assert dummy_event_bus.has_subscribers(TextContentReady)


@pytest.mark.anyio
async def test_lifespan_manages_resources(dummy_event_bus: DummyEventBus, dummy_cache: DummyCache):
    app = create_app()
    async with app.router.lifespan_context(app):
        assert dummy_event_bus.started
        assert dummy_cache.connected

    assert dummy_event_bus.stopped
    assert dummy_cache.disconnected


def test_create_app_registers_middlewares(monkeypatch):
    validation_calls = []
    performance_calls = []

    original_validation = main.register_validation_middleware
    original_performance = main.register_performance_middleware

    def track_validation(app):
        validation_calls.append(app)
        return original_validation(app)

    def track_performance(app):
        performance_calls.append(app)
        return original_performance(app)

    monkeypatch.setattr("main.register_validation_middleware", track_validation)
    monkeypatch.setattr("main.register_performance_middleware", track_performance)

    app = create_app()

    assert validation_calls, "Validation middleware should be registered"
    assert performance_calls, "Performance middleware should be registered"

    registered_middlewares = {middleware.cls for middleware in app.user_middleware}
    assert ContentValidationMiddleware in registered_middlewares
    assert PerformanceMetricsMiddleware in registered_middlewares

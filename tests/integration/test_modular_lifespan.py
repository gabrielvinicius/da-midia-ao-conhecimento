from types import SimpleNamespace

import pytest

import main
from main import create_app
from src.media_management.api.dependencies import get_media_dependencies
from src.shared.events.domain_events import (
    MediaUploaded,
    NotificationRequested,
    TextContentReady,
)
from src.shared.middleware.performance_middleware import PerformanceMetricsMiddleware
from src.shared.middleware.validation_middleware import ContentValidationMiddleware
from src.text_analysis.api.dependencies import (
    get_text_analysis_dependencies,
)
from src.user_management.api.dependencies import get_auth_dependencies





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

        text_analysis_deps = app.dependency_overrides[get_text_analysis_dependencies]()
        assert text_analysis_deps is not None
        if hasattr(text_analysis_deps, "process_handler"):
            assert text_analysis_deps.process_handler is not None
        else:
            # In lightweight bootstrap, summarization can be skipped entirely.
            assert getattr(text_analysis_deps, "service", None) is None


@pytest.mark.anyio
async def test_event_handlers_registered(dummy_event_bus: DummyEventBus, dummy_cache: DummyCache):
    app = create_app()
    async with app.router.lifespan_context(app):
        assert dummy_event_bus.has_subscribers(MediaUploaded)
        assert dummy_event_bus.has_subscribers(TextContentReady)
        assert dummy_event_bus.has_subscribers(NotificationRequested)


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

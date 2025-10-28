import pytest

from main import create_app
from src.shared.application.modules import ModulesRegistry
from src.shared.events.domain_events import MediaUploaded, TextContentReady


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
    monkeypatch.setattr("main.build_event_bus", lambda: bus)
    return bus


@pytest.fixture
def dummy_cache(monkeypatch) -> DummyCache:
    cache = DummyCache()
    monkeypatch.setattr("main", "cache", cache)
    return cache


@pytest.mark.anyio
async def test_modules_registry_initialized(dummy_event_bus: DummyEventBus, dummy_cache: DummyCache):
    app = create_app()
    async with app.router.lifespan_context(app):
        modules = app.state.modules
        assert isinstance(modules, ModulesRegistry)
        assert modules.auth.auth_service is not None
        assert modules.media_management.queries is not None
        assert modules.summarization.process_handler is not None


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

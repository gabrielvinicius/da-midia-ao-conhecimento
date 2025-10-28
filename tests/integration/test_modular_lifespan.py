import pytest

from main import create_app
from src.shared.application.modules import ModulesRegistry
from src.shared.events.domain_events import MediaUploaded, TextContentReady


@pytest.mark.anyio
async def test_modules_registry_initialized():
    app = create_app()
    async with app.router.lifespan_context(app):
        modules = app.state.modules
        assert isinstance(modules, ModulesRegistry)
        assert modules.auth.auth_service is not None
        assert modules.media_management.queries is not None
        assert modules.summarization.task_scheduler is not None


@pytest.mark.anyio
async def test_event_handlers_registered():
    app = create_app()
    async with app.router.lifespan_context(app):
        event_bus = app.state.modules.event_bus
        assert event_bus.has_subscribers(MediaUploaded)
        assert event_bus.has_subscribers(TextContentReady)

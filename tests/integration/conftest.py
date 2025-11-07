from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import main
from src.user_management.config.settings import AuthSettings


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

    class DummyProcessingService:
        async def handle_media_uploaded(self, *_args, **_kwargs):
            return None

        async def handle_text_content_ready(self, *_args, **_kwargs):
            return None

    dummy_media_module = SimpleNamespace(
        queries=object(),
        upload_service=object(),
        lifecycle_service=object(),
        query_service=object(),
        transcription_service=object(),
        transcription_queries=object(),
        processing_service=DummyProcessingService(),
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

    dummy_user_module = MagicMock()
    dummy_user_module.auth_service = object()
    dummy_user_module.auth_queries = object()
    dummy_user_module.user_service = object()
    dummy_user_module.settings = AuthSettings()
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
import sys
import types

dummy_whisper = types.ModuleType("whisper")
dummy_whisper.load_model = lambda *_, **__: object()
sys.modules.setdefault("whisper", dummy_whisper)

from src.media_processing.infrastructure.dependencies import providers as dependencies


def test_create_speech_recognition_service_returns_registered_provider(monkeypatch):
    class _FakeRecognizer:
        def __init__(self):
            self.created = True

    monkeypatch.setitem(dependencies._SPEECH_RECOGNIZERS, "whisper", _FakeRecognizer)

    service = dependencies.create_speech_recognition_service("whisper")

    assert isinstance(service, _FakeRecognizer)
    assert service.created


def test_create_speech_recognition_service_fallbacks_to_default(monkeypatch):
    service = dependencies.create_speech_recognition_service("provider-inexistente")
    from src.media_processing.infrastructure.dependencies.providers import (
        BasicWhisperRecognizer,
    )
    assert isinstance(service, BasicWhisperRecognizer)

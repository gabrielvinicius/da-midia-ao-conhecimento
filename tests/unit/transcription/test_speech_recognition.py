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

    service = dependencies.get_speech_recognizer("whisper")

    assert isinstance(service, _FakeRecognizer)
    assert service.created


def test_speech_recognizer_without_provider_uses_real_default(monkeypatch):
    """Sem provedor escolhido, deve usar o padrão real, e não o stub vazio."""
    class _DefaultRecognizer:
        pass

    monkeypatch.setitem(dependencies._SPEECH_RECOGNIZERS, "default", _DefaultRecognizer)

    assert isinstance(dependencies.get_speech_recognizer(None), _DefaultRecognizer)
    assert isinstance(dependencies.get_speech_recognizer(""), _DefaultRecognizer)


def test_speech_recognizer_unknown_provider_falls_back_to_default(monkeypatch):
    class _DefaultRecognizer:
        pass

    monkeypatch.setitem(dependencies._SPEECH_RECOGNIZERS, "default", _DefaultRecognizer)

    service = dependencies.get_speech_recognizer("provider-inexistente")

    assert isinstance(service, _DefaultRecognizer)

"""O Faster-Whisper só usa GPU NVIDIA; sem ela, a transcrição vai para a CPU."""
import pytest

from src.media_processing.infrastructure.adapters.transcription.faster_whisper_adapter import (
    resolve_device_and_compute,
)


@pytest.mark.parametrize(
    "device, compute, gpus, expected",
    [
        ("cuda", "float16", 1, ("cuda", "float16")),   # RTX 3060
        ("auto", "default", 1, ("cuda", "float16")),
        ("auto", "default", 0, ("cpu", "int8")),
        ("cpu", "int8", 1, ("cpu", "int8")),           # variante CPU
        ("cpu", "float16", 0, ("cpu", "int8")),        # float16 não existe na CPU
        ("cuda", "float16", 0, ("cpu", "int8")),       # variante AMD: CTranslate2 não vê GPU
        ("cuda", "int8_float16", 0, ("cpu", "int8")),
    ],
)
def test_device_and_compute_type(device, compute, gpus, expected):
    assert resolve_device_and_compute(device, compute, gpus) == expected


@pytest.mark.asyncio
async def test_adapter_returns_the_format_the_service_expects(monkeypatch):
    """O adaptador antes importava um módulo inexistente e nunca carregava."""
    from types import SimpleNamespace

    import src.media_processing.infrastructure.adapters.transcription.faster_whisper_adapter as mod

    calls = {}

    class FakeModel:
        def __init__(self, size, device, compute_type):
            calls["init"] = (size, device, compute_type)

        def transcribe(self, path, **kwargs):
            calls["kwargs"] = kwargs
            segments = (
                SimpleNamespace(start=0.0, end=2.5, text=" Olá turma.", avg_logprob=-0.2),
                SimpleNamespace(start=2.5, end=6.0, text=" Hoje: derivadas.", avg_logprob=-0.3),
            )
            return iter(segments), SimpleNamespace(language="pt", duration=6.0)

    monkeypatch.setattr(mod, "_cuda_device_count", lambda: 0)
    import faster_whisper

    monkeypatch.setattr(faster_whisper, "WhisperModel", FakeModel)

    adapter = mod.FasterWhisperAdapter(model_size="large-v3-turbo", device="cuda", hotwords=" SOLID, YAGNI ")
    result = await adapter.transcribe("/tmp/aula.mp4", language="pt")

    assert calls["init"] == ("large-v3-turbo", "cpu", "int8")
    assert calls["kwargs"]["language"] == "pt" and calls["kwargs"]["vad_filter"] is True
    # Glossário do domínio (WHISPER_HOTWORDS) chega ao modelo como frase
    # pontuada e sem condicionar cada trecho no anterior (evita laços).
    assert calls["kwargs"]["hotwords"] == "Nesta gravação, falamos de SOLID, YAGNI."
    assert calls["kwargs"]["condition_on_previous_text"] is False
    plain = mod.FasterWhisperAdapter(model_size="tiny", hotwords="")
    assert plain.hotwords is None
    assert result["text"] == "Olá turma. Hoje: derivadas."
    assert result["segments"][1] == {"start": 2.5, "end": 6.0, "text": "Hoje: derivadas.", "confidence": -0.3}
    assert result["language"] == "pt" and result["duration"] == 6.0
    assert adapter.model_label == "faster-whisper large-v3-turbo"


def test_openai_whisper_uses_the_configured_model_not_base():
    from src.media_processing.infrastructure.adapters.transcription.openai_whisper_adapter import (
        OpenAIWhisperTranscriber,
    )

    assert OpenAIWhisperTranscriber().model_size == "turbo"  # large-v3-turbo
    assert OpenAIWhisperTranscriber(model_size="small").model_size == "small"

"""Registries de providers do `media_processing`.

Cada registry mapeia o nome do provider para uma factory que retorna o adapter
concreto (infra) que implementa o port (application).
"""
from __future__ import annotations

from typing import Callable, Dict, Any

import structlog

from src.shared.infrastructure.messaging.event_bus import SupportsEventBus

from src.media_processing.application.ports import (
    OCRProviderPort,
    SpeechRecognizer,
    TextExtractorPort,
)
from src.shared.infrastructure.config.settings import settings

logger = structlog.get_logger(__name__)

# Optional adapters; guard imports to avoid missing deps
def _load_fastwhisper():
    try:
        from src.media_processing.infrastructure.adapters.transcription.faster_whisper_adapter import (
            FasterWhisperAdapter,
        )
        return FasterWhisperAdapter
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Provider 'fastwhisper' requer o pacote faster-whisper instalado."
        ) from exc


def _load_huggingface():
    try:
        from src.media_processing.infrastructure.adapters.transcription.huggingface_adapter import (
            HuggingfaceTranscriber,
        )
        return HuggingfaceTranscriber
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Provider 'huggingface' requer deps do transformers instaladas."
        ) from exc


def _load_openai_whisper():
    try:
        from src.media_processing.infrastructure.adapters.transcription.openai_whisper_adapter import (
            OpenAIWhisperTranscriber,
        )
        return OpenAIWhisperTranscriber
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Provider 'openai-whisper' requer o pacote openai-whisper instalado."
        ) from exc

def _load_moondream():
    try:
        from src.media_processing.infrastructure.adapters.visual.moondream_adapter import (
            MoondreamVisualAdapter,
        )
        return MoondreamVisualAdapter
    except ImportError:
        return None

def _load_qwen2_vl():
    try:
        from src.media_processing.infrastructure.adapters.visual.qwen2_vl_adapter import (
            Qwen2VLAdapter,
        )
        return Qwen2VLAdapter
    except ImportError:
        return None

from src.media_processing.infrastructure.adapters.text import (
    ocr_provider_adapter,
    text_extractor_adapter,
)

OCRProvider = ocr_provider_adapter.OCRProvider
TextExtractor = text_extractor_adapter.TextExtractor


from src.media_processing.application.ports import VisualAnalysisPort

_VISUAL_ANALYZERS: Dict[str, Callable[[], VisualAnalysisPort]] = {}
_VISUAL_META: Dict[str, Dict[str, Any]] = {}

def _register_visual_providers():
    # Ollama (modelo multimodal configurado em settings.visual_ollama_model)
    from src.media_processing.infrastructure.adapters.visual.ollama_visual_adapter import (
        OllamaVisualAdapter,
    )

    _VISUAL_ANALYZERS["ollama"] = lambda: OllamaVisualAdapter(
        model=settings.visual_ollama_model, host=settings.ollama_host
    )
    _VISUAL_META["ollama"] = {
        "label": f"Ollama ({settings.visual_ollama_model})",
        "public": True,
        "description": "Usa o modelo multimodal do Ollama para descrever os quadros.",
    }

    # Moondream
    cls_moon = _load_moondream()
    if cls_moon:
        _VISUAL_ANALYZERS["moondream"] = lambda: cls_moon()
        _VISUAL_META["moondream"] = {
            "label": "Moondream 2",
            "public": True,
            "description": "Modelo leve para descrição de imagens.",
        }
    
    # Qwen2-VL
    cls_qwen = _load_qwen2_vl()
    if cls_qwen:
        _VISUAL_ANALYZERS["qwen2-vl"] = lambda: cls_qwen()
        _VISUAL_META["qwen2-vl"] = {
            "label": "Qwen2.5-VL (SOTA)",
            "public": True,
            "description": "Modelo Multimodal 7B SOTA (4-bit).",
        }
    
    # Default
    if "default" in _VISUAL_ANALYZERS:
        _VISUAL_ANALYZERS["default"] = _VISUAL_ANALYZERS["qwen2-vl"]
    elif "moondream" in _VISUAL_ANALYZERS:
        _VISUAL_ANALYZERS["default"] = _VISUAL_ANALYZERS["moondream"]

_register_visual_providers()

_VISUAL_INSTANCES: Dict[str, VisualAnalysisPort] = {}


def get_visual_analyzer(provider: str | None = None) -> VisualAnalysisPort:
    """Uma instância por processo e provedor.

    Antes, cada análise criava um adaptador novo, e o modelo da instância
    anterior ficava na GPU até o coletor de lixo agir. O pipeline chama
    ``release()`` ao terminar a etapa visual; a instância recarrega o modelo
    na próxima análise.
    """
    key = (provider or "default").lower()
    if key not in _VISUAL_ANALYZERS and "default" in _VISUAL_ANALYZERS:
        key = "default"
    factory = _VISUAL_ANALYZERS.get(key)
    if not factory:
        raise RuntimeError("Nenhum provider de análise visual disponível.")
    if key not in _VISUAL_INSTANCES:
        _VISUAL_INSTANCES[key] = factory()
    return _VISUAL_INSTANCES[key]


# ----------------- TTS providers -----------------
from src.media_processing.application.ports.tts_port import TTSProviderPort

def _load_kokoro():
    try:
        from src.media_processing.infrastructure.adapters.audio.kokoro_adapter import (
            KokoroTTSAdapter,
        )
        return KokoroTTSAdapter
    except ImportError:
        return None

_TTS_PROVIDERS: Dict[str, Callable[[], TTSProviderPort]] = {}
_TTS_META: Dict[str, Dict[str, Any]] = {}

def _register_tts_providers():
    cls_kokoro = _load_kokoro()
    if cls_kokoro:
        _TTS_PROVIDERS["kokoro"] = lambda: cls_kokoro()
        _TTS_META["kokoro"] = {
            "label": "Kokoro-82M",
            "public": True,
            "description": "TTS Neural SOTA ultraleve.",
        }
        _TTS_PROVIDERS["default"] = _TTS_PROVIDERS["kokoro"]

_register_tts_providers()

def get_tts_provider(provider: str | None = None) -> TTSProviderPort:
    key = (provider or "default").lower()
    factory = _TTS_PROVIDERS.get(key)
    if not factory:
        if "default" in _TTS_PROVIDERS:
            return _TTS_PROVIDERS["default"]()
        raise RuntimeError(f"Provider TTS '{key}' não encontrado.")
    return factory()

def register_tts_provider(name: str, factory: Callable[[], TTSProviderPort], meta: Dict[str, Any] | None = None):
    _TTS_PROVIDERS[name] = factory
    if meta:
        _TTS_META[name] = meta

def list_tts_providers(public_only: bool = True) -> list[str]:
    return sorted([k for k, v in _TTS_META.items() if not public_only or v.get("public", True)])

def tts_provider_meta(name: str) -> Dict[str, Any]:
    return _TTS_META.get(name, {})


# ----------------- Speech recognizers -----------------
class BasicWhisperRecognizer:
    """Stub recognizer to keep unit paths lightweight."""

    async def transcribe(self, path: str, language: str = "auto"):
        # Em produção, não permitir uso do stub para evitar "sucesso" sem transcrição.
        if settings.app_env.lower() not in ("dev", "development", "local"):
            raise RuntimeError(
                "Provider 'whisper' (stub) não está habilitado em produção. "
                "Configure um provider real (ex.: 'huggingface')."
            )
        return {
            "text": "",
            "language": language,
            "provider": "whisper",
            "segments": [],
        }


_SPEECH_RECOGNIZERS: Dict[str, Callable[[], SpeechRecognizer]] = {
    "whisper": lambda: BasicWhisperRecognizer(),
}
_SPEECH_META: Dict[str, Dict[str, Any]] = {
    "whisper": {
        "label": "Whisper (stub - dev only)",
        "public": False,  # não expor no catálogo em produção
        "description": "Stub de desenvolvimento; não produz transcrição real.",
    },
}
def _register_fastwhisper():
    try:
        cls = _load_fastwhisper()
        _SPEECH_RECOGNIZERS["fastwhisper"] = lambda: cls()
        _SPEECH_META["fastwhisper"] = {
            "label": "Faster-Whisper (CTranslate2)",
            "public": True,
            "description": "Implementação otimizada do Whisper (CPU/GPU).",
        }
    except ImportError:
        pass


def _register_huggingface():
    try:
        cls = _load_huggingface()
        _SPEECH_RECOGNIZERS["huggingface"] = lambda: cls()
        _SPEECH_META["huggingface"] = {
            "label": "Transformers ASR (HF)",
            "public": True,
            "description": "",
        }
    except ImportError:
        pass


def _register_openai_whisper():
    try:
        cls = _load_openai_whisper()
        _SPEECH_RECOGNIZERS["openai-whisper"] = lambda: cls()
        _SPEECH_META["openai-whisper"] = {
            "label": "OpenAI Whisper (original)",
            "public": True,
            "description": "Implementação oficial em PyTorch.",
        }
    except ImportError:
        pass


_register_fastwhisper()
_register_huggingface()
_register_openai_whisper()

# definir default: prioriza fastwhisper, depois openai-whisper, depois huggingface; se nada, mantém stub (não público)
if "fastwhisper" in _SPEECH_RECOGNIZERS:
    _SPEECH_RECOGNIZERS["default"] = _SPEECH_RECOGNIZERS["fastwhisper"]
    _SPEECH_META["default"] = {
        "label": "Faster-Whisper (default)",
        "public": True,
        "description": "Provider padrão de transcrição otimizada.",
    }
elif "openai-whisper" in _SPEECH_RECOGNIZERS:
    _SPEECH_RECOGNIZERS["default"] = _SPEECH_RECOGNIZERS["openai-whisper"]
    _SPEECH_META["default"] = {
        "label": "OpenAI Whisper (default)",
        "public": True,
        "description": "Provider padrão usando modelo oficial.",
    }
elif "huggingface" in _SPEECH_RECOGNIZERS:
    _SPEECH_RECOGNIZERS["default"] = _SPEECH_RECOGNIZERS["huggingface"]
    _SPEECH_META["default"] = {
        "label": "Transformers ASR (HF) (default)",
        "public": True,
        "description": "Provider padrão para transcrição.",
    }
else:
    _SPEECH_RECOGNIZERS["default"] = _SPEECH_RECOGNIZERS["whisper"]
    _SPEECH_META["default"] = {
        "label": "Whisper (stub default)",
        "public": False,
        "description": "Stub de desenvolvimento; configure um provider real.",
    }


def register_speech_recognizer(
    name: str,
    factory: Callable[[], SpeechRecognizer],
    *,
    label: str | None = None,
    description: str | None = None,
    public: bool = True,
) -> None:
    _SPEECH_RECOGNIZERS[name.lower()] = factory
    _SPEECH_META[name.lower()] = {
        "label": label or name,
        "description": description or "",
        "public": public,
    }


def get_speech_recognizer(provider: str | None) -> SpeechRecognizer:
    """Resolve o reconhecedor de fala.

    Sem provedor informado (ou com um nome desconhecido), usa o padrão real
    ("default": Faster-Whisper, openai-whisper ou HuggingFace, nessa ordem).
    Antes, caía no stub "whisper", que devolvia uma transcrição vazia.
    """
    key = (provider or "default").lower()
    factory = (
        _SPEECH_RECOGNIZERS.get(key)
        or _SPEECH_RECOGNIZERS.get("default")
        or _SPEECH_RECOGNIZERS["whisper"]
    )
    if provider and key not in _SPEECH_RECOGNIZERS:
        logger.warning("speech_recognizer.unknown_provider_using_default", provider=provider)
    return factory()

def list_speech_recognizers(public_only: bool = True) -> list[str]:
    names = sorted(_SPEECH_RECOGNIZERS.keys())
    if not public_only:
        return names
    return [n for n in names if _SPEECH_META.get(n, {}).get("public", True)]


def speech_recognizer_meta(name: str) -> Dict[str, Any]:
    return _SPEECH_META.get(name, {"label": name, "description": "", "public": True})


# ----------------- Text extractors -----------------
_TEXT_EXTRACTORS: Dict[str, Callable[[], TextExtractorPort]] = {
    "default": lambda: TextExtractor(),
}
_TEXT_META: Dict[str, Dict[str, Any]] = {
    "default": {"label": "Text extractor padrão", "public": True, "description": ""},
}


def register_text_extractor(
    name: str,
    factory: Callable[[], TextExtractorPort],
    *,
    label: str | None = None,
    description: str | None = None,
    public: bool = True,
) -> None:
    _TEXT_EXTRACTORS[name.lower()] = factory
    _TEXT_META[name.lower()] = {
        "label": label or name,
        "description": description or "",
        "public": public,
    }


def get_text_extractor(provider: str | None = None) -> TextExtractorPort:
    key = (provider or "default").lower()
    factory = _TEXT_EXTRACTORS.get(key) or _TEXT_EXTRACTORS["default"]
    return factory()

def list_text_extractors(public_only: bool = True) -> list[str]:
    names = sorted(_TEXT_EXTRACTORS.keys())
    if not public_only:
        return names
    return [n for n in names if _TEXT_META.get(n, {}).get("public", True)]


def text_extractor_meta(name: str) -> Dict[str, Any]:
    return _TEXT_META.get(name, {"label": name, "description": "", "public": True})


# ----------------- OCR providers -----------------
_OCR_PROVIDERS: Dict[str, Callable[[], OCRProviderPort]] = {
    "default": lambda: OCRProvider(),
}
_OCR_META: Dict[str, Dict[str, Any]] = {
    "default": {"label": "OCR padrão", "public": True, "description": ""},
}


def register_ocr_provider(
    name: str,
    factory: Callable[[], OCRProviderPort],
    *,
    label: str | None = None,
    description: str | None = None,
    public: bool = True,
) -> None:
    _OCR_PROVIDERS[name.lower()] = factory
    _OCR_META[name.lower()] = {
        "label": label or name,
        "description": description or "",
        "public": public,
    }


def get_ocr_provider(provider: str | None = None) -> OCRProviderPort:
    key = (provider or "default").lower()
    factory = _OCR_PROVIDERS.get(key) or _OCR_PROVIDERS["default"]
    return factory()

def list_ocr_providers(public_only: bool = True) -> list[str]:
    names = sorted(_OCR_PROVIDERS.keys())
    if not public_only:
        return names
    return [n for n in names if _OCR_META.get(n, {}).get("public", True)]


def ocr_provider_meta(name: str) -> Dict[str, Any]:
    return _OCR_META.get(name, {"label": name, "description": "", "public": True})

def get_event_bus(event_bus: SupportsEventBus | None = None) -> SupportsEventBus:
    """Retorna o event bus recebido do bootstrap; falha se não for fornecido."""
    if event_bus is None:
        raise RuntimeError(
            "MediaProcessing event bus não foi fornecido. Passe via bootstrap/tasks "
            "para evitar acoplamento a estado global."
        )
    return event_bus


__all__ = [
    "get_speech_recognizer",
    "register_speech_recognizer",
    "list_speech_recognizers",
    "speech_recognizer_meta",
    "get_text_extractor",
    "register_text_extractor",
    "list_text_extractors",
    "text_extractor_meta",
    "get_ocr_provider",
    "register_ocr_provider",
    "list_ocr_providers",
    "ocr_provider_meta",
    "get_visual_analyzer",
    "get_event_bus",
    "get_tts_provider",
]

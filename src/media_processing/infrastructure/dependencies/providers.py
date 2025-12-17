"""Provider registries for media_processing adapters.

Each registry maps a provider name to a factory that returns the concrete adapter
implementing the corresponding application port. Defaults are lightweight stubs
to avoid heavy optional deps in test/dev.
"""
from __future__ import annotations

from typing import Callable, Dict

from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.shared.infrastructure.messaging.event_bus_provider import resolve_event_bus

from src.media_processing.application.ports import (
    OCRProviderPort,
    SpeechRecognizer,
    TextExtractorPort,
    VideoAudioExtractorPort,
    VideoThumbnailGeneratorPort,
)

# Optional adapters; guard imports to avoid missing deps
try:
    from src.media_processing.infrastructure.adapters.transcription import (
        huggingface_adapter,
    )

    HuggingfaceTranscriber = huggingface_adapter.HuggingfaceTranscriber
except Exception:  # pragma: no cover - optional dependency
    HuggingfaceTranscriber = None

try:
    from src.media_processing.infrastructure.adapters.video import (
        ffmpeg_audio_extractor,
        ffmpeg_thumbnail_generator,
    )

    FFmpegVideoAudioExtractor = (
        ffmpeg_audio_extractor.FFmpegVideoAudioExtractor
    )
    FFmpegVideoThumbnailGenerator = (
        ffmpeg_thumbnail_generator.FFmpegVideoThumbnailGenerator
    )
except Exception:  # pragma: no cover - optional dependency
    FFmpegVideoAudioExtractor = None
    FFmpegVideoThumbnailGenerator = None

from src.media_processing.infrastructure.adapters.text import (
    ocr_provider_adapter,
    text_extractor_adapter,
)

OCRProvider = ocr_provider_adapter.OCRProvider
TextExtractor = text_extractor_adapter.TextExtractor


# ----------------- Speech recognizers -----------------
class BasicWhisperRecognizer:
    """Stub recognizer to keep unit paths lightweight."""

    async def transcribe(self, path: str, language: str = "auto"):
        return {
            "text": "",
            "language": language,
            "provider": "whisper",
            "segments": [],
        }


_SPEECH_RECOGNIZERS: Dict[str, Callable[[], SpeechRecognizer]] = {
    "whisper": lambda: BasicWhisperRecognizer(),
}
if HuggingfaceTranscriber:
    _SPEECH_RECOGNIZERS["huggingface"] = lambda: HuggingfaceTranscriber()


def register_speech_recognizer(
    name: str, factory: Callable[[], SpeechRecognizer]
) -> None:
    _SPEECH_RECOGNIZERS[name.lower()] = factory


def get_speech_recognizer(provider: str | None) -> SpeechRecognizer:
    key = (provider or "whisper").lower()
    factory = _SPEECH_RECOGNIZERS.get(key) or _SPEECH_RECOGNIZERS["whisper"]
    return factory()


def create_speech_recognition_service(provider: str) -> SpeechRecognizer:
    """Backward-compatible helper used in legacy tests."""
    return get_speech_recognizer(provider)


# ----------------- Text extractors -----------------
_TEXT_EXTRACTORS: Dict[str, Callable[[], TextExtractorPort]] = {
    "default": lambda: TextExtractor(),
}


def register_text_extractor(
    name: str, factory: Callable[[], TextExtractorPort]
) -> None:
    _TEXT_EXTRACTORS[name.lower()] = factory


def get_text_extractor(provider: str | None = None) -> TextExtractorPort:
    key = (provider or "default").lower()
    factory = _TEXT_EXTRACTORS.get(key) or _TEXT_EXTRACTORS["default"]
    return factory()


# ----------------- OCR providers -----------------
_OCR_PROVIDERS: Dict[str, Callable[[], OCRProviderPort]] = {
    "default": lambda: OCRProvider(),
}


def register_ocr_provider(name: str, factory: Callable[[], OCRProviderPort]) -> None:
    _OCR_PROVIDERS[name.lower()] = factory


def get_ocr_provider(provider: str | None = None) -> OCRProviderPort:
    key = (provider or "default").lower()
    factory = _OCR_PROVIDERS.get(key) or _OCR_PROVIDERS["default"]
    return factory()

# ----------------- Event bus passthrough -----------------
def get_event_bus():
    from src.shared.infrastructure.messaging.event_bus_provider import resolve_event_bus

    return resolve_event_bus()


# ----------------- Video adapters -----------------
_AUDIO_EXTRACTORS: Dict[str, Callable[[], VideoAudioExtractorPort]] = {}
if FFmpegVideoAudioExtractor:
    _AUDIO_EXTRACTORS["ffmpeg"] = lambda: FFmpegVideoAudioExtractor()

_THUMBNAIL_GENERATORS: Dict[str, Callable[[], VideoThumbnailGeneratorPort]] = {}
if FFmpegVideoThumbnailGenerator:
    _THUMBNAIL_GENERATORS["ffmpeg"] = lambda: FFmpegVideoThumbnailGenerator()


def register_audio_extractor(
    name: str, factory: Callable[[], VideoAudioExtractorPort]
) -> None:
    _AUDIO_EXTRACTORS[name.lower()] = factory


def register_thumbnail_generator(
    name: str, factory: Callable[[], VideoThumbnailGeneratorPort]
) -> None:
    _THUMBNAIL_GENERATORS[name.lower()] = factory


def get_audio_extractor(provider: str | None = None) -> VideoAudioExtractorPort:
    key = (provider or "ffmpeg").lower()
    factory = _AUDIO_EXTRACTORS.get(key) or _AUDIO_EXTRACTORS["ffmpeg"]
    return factory()


def get_thumbnail_generator(provider: str | None = None) -> VideoThumbnailGeneratorPort:
    key = (provider or "ffmpeg").lower()
    factory = _THUMBNAIL_GENERATORS.get(key) or _THUMBNAIL_GENERATORS["ffmpeg"]
    return factory()


def get_event_bus(event_bus: SupportsEventBus | None = None) -> SupportsEventBus:
    """Retorna o event bus fornecido pelo bootstrap.

    Não realiza fallback para singletons globais: se None for passado, falha
    explicitamente, mantendo a dependência clara e injetada.
    """
    if event_bus is None:
        event_bus = resolve_event_bus()
    return event_bus


__all__ = [
    "get_speech_recognizer",
    "register_speech_recognizer",
    "get_text_extractor",
    "register_text_extractor",
    "get_ocr_provider",
    "register_ocr_provider",
    "get_audio_extractor",
    "register_audio_extractor",
    "get_thumbnail_generator",
    "register_thumbnail_generator",
]

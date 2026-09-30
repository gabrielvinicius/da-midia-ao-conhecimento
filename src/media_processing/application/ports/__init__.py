from __future__ import annotations

from typing import Callable, Protocol

from src.media_processing.domain import Transcription
from src.shared.infrastructure.observability.ports import LoggerPort as SharedLoggerPort
from src.shared.infrastructure.observability.ports import (
    MetricsPort as SharedMetricsPort,
)
from src.storage.domain.value_objects.file_path import FilePath


class StoragePort(Protocol):
    async def retrieve(self, path: FilePath) -> bytes | None:
        ...


class TranscriptionRepositoryPort(Protocol):
    async def save(self, transcription: Transcription) -> Transcription:
        ...

    async def get_by_id(self, transcription_id):
        ...

    async def get_by_media_id(self, media_id):
        ...


class TranscriptionQueryPort(Protocol):
    async def get_by_media_id(self, media_id):
        ...

    async def get_by_id(self, transcription_id):
        ...


class TranscriptionTaskSchedulerPort(Protocol):
    async def schedule_transcription(
        self,
        *,
        transcription_id,
        media_id,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        file_size_bytes: int = 0,
        summarization_provider: str | None = None,
        sentiment_provider: str | None = None,
        topic_modeling_provider: str | None = None,
        user_id: str | None = None,
        filename: str | None = None,
        triggered_by: str | None = None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ):
        ...


class TextExtractionTaskSchedulerPort(Protocol):
    async def schedule_text_extraction(
        self,
        *,
        media_id,
        file_path: str,
        storage_provider: str,
        user_id: str | None = None,
        filename: str | None = None,
        triggered_by: str | None = None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ):
        ...


class SpeechRecognizer(Protocol):
    async def transcribe(self, path: str, language: str):
        ...


SpeechRecognizerFactory = Callable[[str], SpeechRecognizer]


class MetricsPort(SharedMetricsPort, Protocol):
    ...


class OperationLoggerPort(SharedLoggerPort, Protocol):
    ...


class TextExtractorPort(Protocol):
    async def extract(self, file_path: str, mime_type: str) -> str:
        ...


class OCRProviderPort(Protocol):
    async def extract(self, file_path: str) -> str:
        ...


class VisualAnalysisPort(Protocol):
    """Port for multimodal AI to 'see' and describe video frames."""
    async def describe_frame(self, frame_bytes: bytes, prompt: str = "Describe this scene in detail.") -> str:
        ...


class VideoFrameExtractorPort(Protocol):
    """Port for extracting raw frames from video data."""
    async def extract_frame(self, video_data: bytes, timestamp: float) -> bytes:
        ...

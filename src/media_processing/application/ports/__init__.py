from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Callable, List, Optional, Protocol
from uuid import UUID

from src.media_processing.domain import Transcription
from src.shared.domain.events import MediaUploaded
from src.shared.application.observability import LoggerPort as SharedLoggerPort
from src.shared.application.observability import (
    MetricsPort as SharedMetricsPort,
)


class StoragePort(Protocol):
    async def download_to(self, path: str, destination: str) -> bool:
        """Grava o arquivo em ``destination``; False se ele não existir."""
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

    async def release(self) -> None:
        """Libera a memória do modelo de visão (a próxima chamada o recarrega)."""
        ...


class VideoFrameExtractorPort(Protocol):
    """Extrai quadros de um vídeo."""
    async def extract_frames(self, video_path: str, timestamps: list[float]) -> list[Optional[bytes]]:
        """Um quadro (JPEG) por instante, na mesma ordem; None se falhar.

        Lê o vídeo já em disco (o mesmo arquivo usado pela transcrição).
        """
        ...


class UnfinishedTranscriptionsPort(Protocol):
    async def list_unfinished(self, started_before: datetime.datetime) -> List[Transcription]:
        """Transcrições pendentes ou em andamento sem atualização desde o instante dado."""
        ...


class TranscriptionResultPort(Protocol):
    async def process_transcription_result(
        self,
        transcription_id: UUID,
        media_id: UUID,
        result_data: dict,
        provider: str,
        success: bool,
        error_message: Optional[str] = None,
        *,
        final_attempt: bool = False,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Registra o resultado (ou a falha) de uma transcrição e avisa os interessados."""
        ...


class VisualDescriberPort(Protocol):
    """Descreve alguns quadros de uma gravação de vídeo (VisualDescriptionService)."""
    async def describe_recording(
        self, video_path: str, size_bytes: int, duration: Optional[float]
    ) -> list[str]:
        """Descrições "[mm:ss] texto"; lista vazia para áudio ou sem duração."""
        ...


class MediaDurationProbe(Protocol):
    """Lê a duração (em segundos) de um arquivo de áudio ou vídeo."""
    async def duration_seconds(self, file_path: str) -> float | None:
        ...


class RealtimeFactorPort(Protocol):
    """Tempo de processamento por segundo de gravação, medido no histórico."""
    async def realtime_factor(self, task_type: str) -> float | None:
        ...


class ProcessingTaskTerminator(Protocol):
    """Encerra a tarefa do worker que ainda processa uma transcrição."""
    async def terminate(self, transcription_id: str, media_id: str) -> bool:
        ...


class AnalysisRequestPort(Protocol):
    def request_analysis(self, payload: dict) -> None:
        """Pede a análise do texto pronto (feita pelo módulo text_analysis)."""
        ...

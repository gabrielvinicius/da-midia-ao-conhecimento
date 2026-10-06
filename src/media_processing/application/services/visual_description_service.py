"""Descreve alguns quadros de um vídeo, logo após a transcrição.

A descrição é parte do processamento da mídia, como a transcrição: fica no
mesmo worker, que já tem o arquivo em mãos, e é guardada no resultado da
transcrição. A análise de texto recebe só as descrições prontas e não
conhece modelos de visão nem o arquivo de vídeo.
"""
from __future__ import annotations

import time
from typing import List, Optional

import structlog

from src.media_processing.application.ports import (
    VideoFrameExtractorPort,
    VisualAnalysisPort,
)
from src.media_processing.domain.visual_sampling import frame_timestamps, is_video_file
from src.shared.application.ports import ProcessingStatsPort
from src.shared.domain.time.timestamps import format_timestamp

logger = structlog.get_logger(__name__)

PROMPT = (
    "Describe concisely what is shown in this video frame: any text, slide, "
    "formula, chart or diagram on screen, and what the people are doing."
)


class VisualDescriptionService:
    def __init__(
        self,
        analyzer: VisualAnalysisPort,
        extractor: VideoFrameExtractorPort,
        stats: Optional[ProcessingStatsPort] = None,
    ) -> None:
        self._analyzer = analyzer
        self._extractor = extractor
        self._stats = stats

    async def describe_recording(
        self, video_path: str, size_bytes: int, duration: Optional[float]
    ) -> List[str]:
        """Descreve os quadros se a gravação for um vídeo com duração conhecida,
        e registra quanto tempo isso levou ("visual_description")."""
        if not is_video_file(video_path) or not duration:
            return []
        started = time.perf_counter()
        descriptions = await self.describe(video_path, float(duration))
        if self._stats:
            try:
                await self._stats.log_stat(
                    "visual_description",
                    time.perf_counter() - started,
                    size_bytes,
                    float(duration),
                    getattr(self._analyzer, "model_label", None),
                    "success" if descriptions else "failed",
                )
            except Exception as exc:  # estatística nunca derruba o processamento
                logger.warning("visual_description.stats_record_failed", error=str(exc))
        return descriptions

    async def describe(self, video_path: str, duration: float) -> List[str]:
        """Descrições "[mm:ss] texto", na ordem do vídeo.

        Os quadros complementam a transcrição; uma falha aqui é registrada e
        devolve o que já foi descrito, sem derrubar o processamento.
        """
        timestamps = frame_timestamps(duration)
        if not timestamps:
            return []
        descriptions: List[str] = []
        try:
            frames = await self._extractor.extract_frames(video_path, timestamps)
            for ts, frame in zip(timestamps, frames):
                if not frame:
                    continue
                text = await self._analyzer.describe_frame(frame, prompt=PROMPT)
                if text and "unavailable" not in text.lower():
                    descriptions.append(f"[{format_timestamp(ts)}] {text.strip()}")
        except Exception as exc:
            logger.warning("visual_description.failed", error=str(exc), described=len(descriptions))
        finally:
            await self._release()
        return descriptions

    async def _release(self) -> None:
        # Devolve a memória da GPU antes da análise, que usa o modelo de linguagem.
        try:
            await self._analyzer.release()
        except Exception as exc:
            logger.warning("visual_description.release_failed", error=str(exc))

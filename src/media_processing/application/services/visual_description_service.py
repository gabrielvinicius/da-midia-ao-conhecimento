"""Descreve alguns quadros de um vídeo, logo após a transcrição.

A descrição é parte do processamento da mídia, como a transcrição: fica no
mesmo worker, que já tem o arquivo em mãos, e é guardada no resultado da
transcrição. A análise de texto recebe só as descrições prontas e não
conhece modelos de visão nem o arquivo de vídeo.
"""
from __future__ import annotations

import inspect
from typing import List

import structlog

from src.media_processing.application.ports import (
    VideoFrameExtractorPort,
    VisualAnalysisPort,
)
from src.media_processing.domain.visual_sampling import format_timestamp, frame_timestamps

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
    ) -> None:
        self._analyzer = analyzer
        self._extractor = extractor

    async def describe(self, video_data: bytes, duration: float) -> List[str]:
        """Descrições "[mm:ss] texto", na ordem do vídeo.

        Os quadros complementam a transcrição; uma falha aqui é registrada e
        devolve o que já foi descrito, sem derrubar o processamento.
        """
        timestamps = frame_timestamps(duration)
        if not timestamps:
            return []
        descriptions: List[str] = []
        try:
            frames = await self._extractor.extract_frames(video_data, timestamps)
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
        release = getattr(self._analyzer, "release", None)
        if not release:
            return
        try:
            result = release()
            if inspect.isawaitable(result):
                await result
        except Exception as exc:
            logger.warning("visual_description.release_failed", error=str(exc))

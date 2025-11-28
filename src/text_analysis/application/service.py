"""Application-level service using injected handlers."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.providers.domain.interfaces import IProviderRegistry
from .commands.analyze_text import AnalyzeTextCommand
from .queries.get_analysis import GetAnalysisQuery
from .queries.list_topics import ListTopicsQuery
from .commands.analyze_text import AnalyzeTextCommandHandler
from .queries.get_analysis import GetAnalysisQueryHandler
from .queries.list_topics import ListTopicsQueryHandler
from .metrics import TextAnalysisMetrics, NoOpTextAnalysisMetrics

logger = logging.getLogger(__name__)


class TextAnalysisService:
    """Thin async-friendly wrapper around the domain pipeline."""

    def __init__(
        self,
        *,
        provider_registry: IProviderRegistry | None = None,
        analyze_handler: AnalyzeTextCommandHandler,
        get_handler: GetAnalysisQueryHandler,
        list_topics_handler: ListTopicsQueryHandler,
        metrics: TextAnalysisMetrics | None = None,
    ) -> None:
        self.provider_registry = provider_registry
        self._analyze_handler = analyze_handler
        self._get_handler = get_handler
        self._list_topics_handler = list_topics_handler
        self._metrics = metrics or NoOpTextAnalysisMetrics()

    def _validate_provider(self, provider: Optional[str]) -> Optional[str]:
        if provider and self.provider_registry:
            actives = {p.name for p in self.provider_registry.get_active_providers()}
            if provider not in actives:
                raise ValueError(f"Provider '{provider}' não registrado/ativo")
        return provider

    async def analyze_text_content(
        self,
        *,
        media_id: Optional[str] = None,
        transcription_id: Optional[str] = None,
        text_content: Optional[str],
        segments: Optional[list[dict]] = None,
        language: Optional[str] = None,
        provider: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        import time

        resolved_provider = self._validate_provider(provider)
        start = time.perf_counter()
        success = False
        try:
            cmd = AnalyzeTextCommand(
                text=text_content or "",
                segments=segments,
                language=language,
                chunk_size=options.get("chunk_size") if options else None,
                chunk_overlap=options.get("chunk_overlap") if options else None,
                media_id=media_id,
                transcription_id=transcription_id,
                user_id=user_id,
            )
            dto = self._analyze_handler(cmd)
            result = dto.to_dict()
            # Enrich with ownership/context
            if media_id:
                result["media_id"] = media_id
            if transcription_id:
                result["transcription_id"] = transcription_id
            if resolved_provider:
                result["provider"] = resolved_provider
            if user_id:
                result["user_id"] = user_id
            success = True
            return result
        finally:
            try:
                await self._metrics.record_operation(
                    operation="analyze_text_content",
                    duration=time.perf_counter() - start,
                    success=success,
                    provider=provider or resolved_provider,
                )
            except Exception:
                pass

    async def schedule_summarization_task(self, **kwargs) -> Dict[str, Any]:
        logger.info("schedule_summarization_task", extra=kwargs)
        return await self.analyze_text_content(
            media_id=kwargs.get("media_id"),
            transcription_id=kwargs.get("transcription_id"),
            text_content=kwargs.get("text_content"),
            segments=kwargs.get("segments"),
            language=kwargs.get("language"),
            provider=kwargs.get("provider"),
            options=kwargs.get("options"),
        )

    async def schedule_sentiment_analysis_task(self, **kwargs) -> Dict[str, Any]:
        logger.info("schedule_sentiment_analysis_task", extra=kwargs)
        return await self.analyze_text_content(
            media_id=kwargs.get("media_id"),
            transcription_id=kwargs.get("transcription_id"),
            text_content=kwargs.get("text"),
            segments=kwargs.get("segments"),
            language=kwargs.get("language"),
            provider=kwargs.get("provider"),
            options=kwargs.get("options"),
        )

    async def schedule_topic_modeling_task(self, **kwargs) -> Dict[str, Any]:
        logger.info("schedule_topic_modeling_task", extra=kwargs)
        return await self.analyze_text_content(
            media_id=kwargs.get("media_id"),
            text_content=kwargs.get("text_content"),
            segments=kwargs.get("segments"),
            language=kwargs.get("language"),
            provider=kwargs.get("provider"),
            options=kwargs.get("options"),
        )

    def get_analysis(self, analysis_id: str) -> Dict[str, Any]:
        dto = self._get_handler(GetAnalysisQuery(analysis_id))
        return dto.to_dict()

    def list_topics(self, analysis_id: str) -> list:
        topics = self._list_topics_handler(ListTopicsQuery(analysis_id))
        return [t.__dict__ for t in topics]

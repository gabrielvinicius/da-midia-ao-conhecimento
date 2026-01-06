"""Implementações concretas dos passos do pipeline de análise."""
from __future__ import annotations

import inspect
from typing import Any, Optional
from src.text_analysis.domain import Analysis, SentimentLabel
from src.text_analysis.application.pipeline.base import AnalysisStep
from src.text_analysis.application.ports import (
    ChunkingServicePort,
    EmbeddingServicePort,
    SentimentServicePort,
    TextGenerationPort,
    TopicModelingPort,
)
from statistics import mean

class ChunkingStep(AnalysisStep):
    def __init__(self, chunker: ChunkingServicePort, size: Optional[int] = None, overlap: Optional[int] = None):
        self.chunker = chunker
        self.size = size
        self.overlap = overlap

    @property
    def name(self) -> str:
        return "chunking"

    async def process(self, analysis: Analysis) -> Analysis:
        chunks = self.chunker.chunk(analysis.document, size=self.size, overlap=self.overlap)
        analysis.chunks = chunks
        return analysis


class SentimentStep(AnalysisStep):
    def __init__(self, sentiment_service: SentimentServicePort, language: str):
        self.service = sentiment_service
        self.language = language

    @property
    def name(self) -> str:
        return "sentiment"

    async def process(self, analysis: Analysis) -> Analysis:
        if not analysis.chunks:
            return analysis
        
        sentiments_result = self.service.analyze(analysis.chunks, self.language)
        sentiments = await sentiments_result if inspect.isawaitable(sentiments_result) else sentiments_result
        analysis.sentiments = sentiments
        
        # Aggregate Overall
        if sentiments:
            positives = [s.score for s in sentiments if s.label == SentimentLabel.POSITIVE]
            negatives = [s.score for s in sentiments if s.label == SentimentLabel.NEGATIVE]
            neutrals = [s.score for s in sentiments if s.label == SentimentLabel.NEUTRAL]
            pos = mean(positives) if positives else 0.0
            neg = mean(negatives) if negatives else 0.0
            neu = mean(neutrals) if neutrals else 0.0
            scores = {
                SentimentLabel.POSITIVE: pos,
                SentimentLabel.NEUTRAL: neu,
                SentimentLabel.NEGATIVE: neg,
            }
            analysis.overall_sentiment = max(scores, key=scores.get)
            
        return analysis


class TopicModelingStep(AnalysisStep):
    def __init__(self, topic_modeling: TopicModelingPort, embedding_service: EmbeddingServicePort, language: str):
        self.topic_modeling = topic_modeling
        self.embedding_service = embedding_service
        self.language = language

    @property
    def name(self) -> str:
        return "topic_modeling"

    async def process(self, analysis: Analysis) -> Analysis:
        if not analysis.chunks:
            return analysis
        
        embeddings_result = self.embedding_service.embed([chunk.text for chunk in analysis.chunks])
        embeddings = await embeddings_result if inspect.isawaitable(embeddings_result) else embeddings_result

        topics, diagnostics = await self.topic_modeling.model_topics(analysis.chunks, embeddings, self.language)
        analysis.topics = topics
        analysis.diagnostics.update(diagnostics)
        return analysis


class SummarizationStep(AnalysisStep):
    def __init__(self, text_generation: TextGenerationPort, language: str, advisor: Optional[Any] = None):
        self.text_generation = text_generation
        self.language = language
        self.advisor = advisor

    @property
    def name(self) -> str:
        return "summarization"

    async def process(self, analysis: Analysis) -> Analysis:
        if not analysis.topics:
            return analysis
        
        # Intelligent Check
        if self.advisor:
            from src.shared.infrastructure.monitoring.hardware_advisor import SystemPressure
            pressure = self.advisor.recommend_strategy()
            if pressure == SystemPressure.CRITICAL:
                logger.warning("pipeline.summarization_skipped_due_to_critical_pressure")
                return analysis
        
        summary_parts = []
        for topic in analysis.topics:
            summary_md = await self._summarize_with_redundancy(topic, analysis)
            if summary_md:
                topic.summary = summary_md
                summary_parts.append(summary_md)
        
        if summary_parts:
            analysis.summary = "\n\n".join(summary_parts)
            
        return analysis

    async def _summarize_with_redundancy(self, topic: Any, analysis: Analysis) -> Optional[str]:
        """Tenta gerar o resumo usando o plano de redundância ativa."""
        primary = getattr(self.text_generation, "provider_name", "primary")
        providers_to_try = [self.text_generation]
        
        if self.advisor:
            # Se o primário estiver doente ou falhar, o advisor sugere outros
            # Aqui poderíamos instanciar outros adaptadores via Factory
            pass 

        try:
            if self.text_generation.is_available():
                result = await self.text_generation.summarize_topic(
                    topic.title, "\n".join(topic.snippets), topic.keywords, self.language
                )
                if self.advisor: self.advisor.report_success(primary)
                return result
        except Exception as exc:
            logger.error("pipeline.primary_summarization_failed", provider=primary, error=str(exc))
            if self.advisor: self.advisor.report_failure(primary)
            # Fallback automático para Heurística (Redundância Interna)
            return self._fallback_heuristic(topic)
        
        return None

    def _fallback_heuristic(self, topic: Any) -> str:
        """Redundância final: Resumo baseado em extração de frases-chave."""
        bullets = "\n".join(f"- {kw}" for kw in topic.keywords[:5])
        return f"# {topic.title or 'Tópico'}\n## Resumo (Automático)\n{bullets}\n"


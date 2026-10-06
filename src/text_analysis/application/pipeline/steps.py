"""Etapas do pipeline de análise.

Ordem (ver pipeline_factory): trechos → sentimento → temas → indexação →
liberação de memória → títulos dos temas → síntese → verificação de
fidelidade. As descrições dos quadros de vídeo chegam prontas, com a
transcrição (media_processing), em ``analysis.visual_context``.

As etapas que usam modelos locais (no worker) vêm antes das que usam o modelo
de linguagem (no Ollama), e a memória da GPU é devolvida entre os dois grupos:
numa placa de 12 GB não cabem todos juntos.
"""
from __future__ import annotations

import re
from typing import Optional, Sequence

import structlog

from src.text_analysis.application.pipeline.base import AnalysisStep
from src.text_analysis.application.ports import (
    ChunkingServicePort,
    EmbeddingServicePort,
    ReleasablePort,
    SentimentServicePort,
    TextGenerationPort,
    TextGenerationUnavailableError,
    TopicModelingPort,
    VectorIndexPort,
)
from src.text_analysis.application.pipeline.synthesis import APPENDIX_MARKER, language_name
from src.text_analysis.domain import Analysis, SummarySource
from src.text_analysis.domain.content_profile import main_topics, overall_sentiment, sentiment_distribution
from src.text_analysis.domain.grounding import assess_grounding, split_sentences

logger = structlog.get_logger(__name__)

def _analysis_language(analysis: Analysis, default: str) -> str:
    """Idioma detectado na transcrição (para palavras vazias e sentimento)."""
    return analysis.language_or(default)


class ChunkingStep(AnalysisStep):
    required = True

    def __init__(self, chunker: ChunkingServicePort, size: Optional[int] = None, overlap: Optional[int] = None):
        self.chunker = chunker
        self.size = size
        self.overlap = overlap

    @property
    def name(self) -> str:
        return "chunking"

    async def process(self, analysis: Analysis) -> Analysis:
        analysis.chunks = self.chunker.chunk(analysis.document, size=self.size, overlap=self.overlap)
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
        language = _analysis_language(analysis, self.language)
        sentiments = self.service.analyze(analysis.chunks, language)
        analysis.sentiments = sentiments
        if sentiments:
            analysis.overall_sentiment = overall_sentiment(sentiments)
            analysis.diagnostics["sentiment_distribution"] = sentiment_distribution(sentiments)
        return analysis


class ChunkEmbeddingStep(AnalysisStep):
    """Calcula os vetores dos trechos uma vez, para os temas, a busca e a fidelidade."""

    required = True

    def __init__(self, embedding_service: EmbeddingServicePort):
        self.embedding_service = embedding_service

    @property
    def name(self) -> str:
        return "chunk_embedding"

    async def process(self, analysis: Analysis) -> Analysis:
        if not analysis.chunks:
            return analysis
        embeddings = self.embedding_service.embed([chunk.text for chunk in analysis.chunks])
        analysis.chunk_embeddings = [e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings]
        return analysis


class TopicModelingStep(AnalysisStep):
    """Agrupa os trechos em temas, reaproveitando os vetores já calculados."""

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
        if len(analysis.chunk_embeddings or []) != len(analysis.chunks):
            await ChunkEmbeddingStep(self.embedding_service).process(analysis)
        embeddings = analysis.chunk_embeddings

        topics, diagnostics = await self.topic_modeling.model_topics(
            analysis.chunks, embeddings, _analysis_language(analysis, self.language)
        )
        analysis.topics = topics
        analysis.diagnostics.update(diagnostics)
        return analysis


class KnowledgeIndexingStep(AnalysisStep):
    """Grava trechos e vetores no pgvector para a busca semântica."""

    required = True

    def __init__(self, vector_repository: VectorIndexPort):
        self.vector_repo = vector_repository

    @property
    def name(self) -> str:
        return "knowledge_indexing"

    async def process(self, analysis: Analysis) -> Analysis:
        embeddings = analysis.chunk_embeddings
        if not analysis.media_id or not analysis.chunks or not embeddings:
            analysis.diagnostics["indexed_chunks"] = 0
            return analysis
        if len(embeddings) != len(analysis.chunks):
            logger.warning("knowledge_indexing.size_mismatch", chunks=len(analysis.chunks), embeddings=len(embeddings))

        records = [
            {
                "text": chunk.text,
                "embedding": list(vector),
                "metadata": {
                    "chunk_id": chunk.id,
                    "start": chunk.start,
                    "end": chunk.end,
                    "analysis_id": str(analysis.id),
                },
            }
            for chunk, vector in zip(analysis.chunks, embeddings)
        ]
        await self.vector_repo.save_chunks(analysis.media_id, records, user_id=analysis.user_id)
        analysis.diagnostics["indexed_chunks"] = len(records)
        logger.info("knowledge_indexing.saved", media_id=str(analysis.media_id), count=len(records))
        return analysis


class ReleaseMemoryStep(AnalysisStep):
    """Devolve ao driver a memória da GPU retida pelos modelos do worker.

    O PyTorch guarda a memória que liberou para reutilizá-la; sem devolvê-la,
    o Ollama, que é outro processo, não a encontra disponível.
    """

    def __init__(self, releasables: Sequence[ReleasablePort]):
        self.releasables = list(releasables)

    @property
    def name(self) -> str:
        return "release_memory"

    async def process(self, analysis: Analysis) -> Analysis:
        for resource in self.releasables:
            await resource.release()
        return analysis


class TopicTitleStep(AnalysisStep):
    """Títulos legíveis para os temas, numa única chamada ao modelo de linguagem.

    Se nenhum modelo responder ou a resposta não puder ser interpretada, os
    títulos do BERTopic são mantidos.
    """

    _LINE = re.compile(r"^\s*[-*]?\s*(-?\d+)\s*[:.)\-–]\s*(.+?)\s*$")

    def __init__(self, text_generation: TextGenerationPort, language: str, max_words: int = 8):
        self.text_generation = text_generation
        self.language = language
        self.max_words = max_words

    @property
    def name(self) -> str:
        return "topic_titles"

    async def process(self, analysis: Analysis) -> Analysis:
        topics = main_topics(analysis.topics)
        if not topics or not self.text_generation.is_available():
            return analysis

        blocks = []
        for t in topics:
            snippets = "\n".join(f"  - {sn}" for sn in (t.snippets or [])[:3])
            blocks.append(f"{t.id}: palavras-chave: {', '.join((t.keywords or [])[:8])}\n{snippets}")
        prompt = (
            "<<<SYSTEM>>>\nVocê dá títulos curtos e descritivos a temas extraídos de uma transcrição.\n<<<END_SYSTEM>>>\n"
            f"Para cada tema abaixo, escreva um título de no máximo {self.max_words} palavras, "
            f"em {language_name(self.language)}, baseado apenas nas palavras-chave e nos trechos.\n"
            "Responda somente com uma linha por tema, no formato `id: título`, sem aspas nem explicações.\n\n"
            + "\n\n".join(blocks)
        )
        try:
            response = await self.text_generation.summarize_topic("Títulos dos temas", prompt, [], self.language)
        except TextGenerationUnavailableError:
            analysis.diagnostics["topic_titles_source"] = "bertopic"
            return analysis

        titles = self.parse_titles(response or "")
        for t in topics:
            if t.id in titles:
                t.title = titles[t.id]
        analysis.diagnostics["topic_titles_source"] = "llm" if titles else "bertopic"
        return analysis

    def parse_titles(self, text: str) -> dict[int, str]:
        titles: dict[int, str] = {}
        for line in text.splitlines():
            match = self._LINE.match(line)
            if not match:
                continue
            title = match.group(2).strip().strip('"\'`*').strip()
            if title:
                titles[int(match.group(1))] = " ".join(title.split()[: self.max_words])
        return titles



class GroundingCheckStep(AnalysisStep):
    """Verifica, frase a frase, se o resumo tem apoio na transcrição.

    Cada frase do resumo (sem o apêndice) é comparada, pelos mesmos vetores da
    busca, com todos os trechos da gravação. Frases sem nenhum trecho
    parecido o bastante são listadas para conferência. Ver
    ``domain.grounding`` sobre o que a verificação detecta e o que não.
    """

    def __init__(self, embedding_service: EmbeddingServicePort, threshold: float = 0.80):
        self.embedding_service = embedding_service
        self.threshold = threshold

    @property
    def name(self) -> str:
        return "grounding_check"

    async def process(self, analysis: Analysis) -> Analysis:
        if not analysis.summary or not analysis.chunks:
            return analysis
        if analysis.summary_source == SummarySource.SIMPLIFIED:
            return analysis  # montado dos próprios temas: não há o que verificar
        body = analysis.summary.split(APPENDIX_MARKER, 1)[0]
        sentences = split_sentences(body)
        if not sentences:
            return analysis

        passages = analysis.chunk_embeddings
        if len(passages) != len(analysis.chunks):
            passages = self.embedding_service.embed([c.text for c in analysis.chunks])
        queries = self.embedding_service.embed(sentences, kind="query")
        report = assess_grounding(
            sentences, queries, passages, [c.start for c in analysis.chunks], self.threshold
        )
        analysis.grounding = report
        return analysis

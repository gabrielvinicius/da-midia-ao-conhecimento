"""Implementações concretas dos passos do pipeline de análise."""
from __future__ import annotations

import inspect
from typing import Any, Optional
import structlog
from src.text_analysis.domain import Analysis, SentimentLabel
from src.text_analysis.application.pipeline.base import AnalysisStep
from src.text_analysis.application.ports import (
    ChunkingServicePort,
    EmbeddingServicePort,
    SentimentServicePort,
    TextGenerationPort,
    TopicModelingPort,
)
from src.media_processing.application.ports import VideoFrameExtractorPort, VisualAnalysisPort
from src.storage.application.ports import StorageServiceResolverPort
from statistics import mean

logger = structlog.get_logger(__name__)

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

        # Store embeddings in diagnostics temporarily for the IndexingStep
        analysis.diagnostics["_temp_embeddings"] = [e.tolist() if hasattr(e, 'tolist') else e for e in embeddings]

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
        
        # Recupera contexto visual (Level 7.0+)
        visual_context = analysis.diagnostics.get("visual_context", [])
        visual_text = "\n".join(visual_context) if visual_context else ""

        summary_parts = []
        for topic in analysis.topics:
            # Injeta contexto visual se relevante para o tempo do tópico (heurística simples ou global)
            # Para Level 8.3, passamos o contexto visual global para enriquecer
            summary_md = await self._summarize_with_redundancy(topic, visual_text, analysis)
            if summary_md:
                topic.summary = summary_md
                summary_parts.append(summary_md)
        
        # Nota: A unificação final ("Master Summary") ocorre no SynthesisStep
        return analysis

    async def _summarize_with_redundancy(self, topic: Any, visual_context: str, analysis: Analysis) -> Optional[str]:
        """Tenta gerar o resumo usando o plano de redundância ativa."""
        primary = getattr(self.text_generation, "provider_name", "primary")
        
        # Prompt Inquiry-Based (SOTA 2025)
        context_prompt = ""
        if visual_context:
            context_prompt = f"\n[CONTEXTO VISUAL DO VÍDEO]:\n{visual_context}\n"

        prompt_instruction = (
            f"Analise o texto abaixo sobre '{topic.title}'. {context_prompt}\n"
            "Identifique as 3 principais teses defendidas e as evidências citadas. "
            "Se houver contexto visual, correlacione com o texto. "
            f"Responda em {self.language} com formatação Markdown estruturada."
        )
        
        try:
            if self.text_generation.is_available():
                # Passamos o prompt customizado. Adapters devem suportar 'instruction' ou concatenar.
                # Aqui assumimos que o adapter usa (title, text, keywords)
                # Vamos injetar a instrução no 'text' ou 'title' se o adapter for rígido,
                # ou idealmente, o adapter aceita um prompt template.
                # Para compatibilidade, concatenamos no texto.
                enriched_text = f"{prompt_instruction}\n\n[TEXTO]:\n" + "\n".join(topic.snippets)
                
                result = await self.text_generation.summarize_topic(
                    topic.title, enriched_text, topic.keywords, self.language
                )
                if self.advisor: self.advisor.report_success(primary)
                return result
        except Exception as exc:
            logger.error("pipeline.primary_summarization_failed", provider=primary, error=str(exc))
            if self.advisor: self.advisor.report_failure(primary)
            return self._fallback_heuristic(topic)
        
        return None

    def _fallback_heuristic(self, topic: Any) -> str:
        """Redundância final: Resumo baseado em extração de frases-chave."""
        bullets = "\n".join(f"- {kw}" for kw in topic.keywords[:5])
        return f"# {topic.title or 'Tópico'}\n## Resumo (Automático)\n{bullets}\n"


class KnowledgeIndexingStep(AnalysisStep):
    def __init__(self, vector_repository: Any):
        self.vector_repo = vector_repository

    @property
    def name(self) -> str:
        return "knowledge_indexing"

    async def process(self, analysis: Analysis) -> Analysis:
        # Se houver embeddings temporários, salvá-los
        if "_temp_embeddings" in analysis.diagnostics:
            # Lógica de persistência vetorial aqui
            # (Simplificado para manter foco no Summarization/Synthesis)
            pass
        return analysis


class SynthesisStep(AnalysisStep):
    """
    Level 8.3: Executive Master Summary.
    Unifies all topic summaries into a cohesive narrative using long-context LLMs.
    """
    def __init__(self, text_generation: TextGenerationPort, language: str):
        self.text_generation = text_generation
        self.language = language

    @property
    def name(self) -> str:
        return "synthesis"

    async def process(self, analysis: Analysis) -> Analysis:
        if not analysis.topics:
            return analysis

        # Coletar todos os resumos parciais
        topic_summaries = [t.summary for t in analysis.topics if t.summary]
        if not topic_summaries:
            return analysis

        combined_text = "\n\n".join(topic_summaries)
        
        # Prompt Hierárquico
        prompt = (
            "Abaixo estão resumos dos principais tópicos de um vídeo.\n"
            f"[RESUMOS PARCIAIS]:\n{combined_text}\n\n"
            "Tarefa: Escreva um 'Resumo Executivo' coeso que conecte todos esses pontos em uma narrativa fluida. "
            "Crie uma introdução que apresente o objetivo do vídeo, desenvolva os argumentos principais "
            "e termine com uma conclusão sintetizadora. "
            f"Escreva em {self.language} profissional."
        )

        try:
            # Usamos o 'summarize_topic' como interface genérica de geração
            # Idealmente, teríamos um método 'generate_text'
            master_summary = await self.text_generation.summarize_topic(
                "Resumo Executivo", prompt, [], self.language
            )
            
            # Adiciona o Resumo Executivo no topo do output final
            analysis.summary = f"# Resumo Executivo\n{master_summary}\n\n---\n# Detalhes por Tópico\n{combined_text}"
            
        except Exception as exc:
            logger.error("synthesis.failed", error=str(exc))
            # Fallback: Apenas concatena (já feito no passo anterior, mas garantimos aqui)
            analysis.summary = combined_text

        return analysis

class VisualInsightStep(AnalysisStep):
    """Level 7.0: Multimodal insight. 'Sees' the video to complement the transcript."""
    
    def __init__(
        self, 
        visual_analyzer: VisualAnalysisPort, 
        frame_extractor: VideoFrameExtractorPort,
        storage_resolver: StorageServiceResolverPort, # Use resolver to get download service
    ):
        self.analyzer = visual_analyzer
        self.extractor = frame_extractor
        self.storage_resolver = storage_resolver

    @property
    def name(self) -> str:
        return "visual_insight"

    async def process(self, analysis: Analysis) -> Analysis:
        if not analysis.media_id or not analysis.document.segments:
            return analysis
            
        try:
            # 1. Estimate duration from segments
            duration = analysis.document.segments[-1].get("end", 0) if analysis.document.segments else 0
            if duration <= 0:
                return analysis

            # 2. Resolve storage and download video data
            # Use diagnostics or assume default provider if not set in Analysis entity (gap check)
            # In Level 6.0, we should have this info.
            provider = analysis.diagnostics.get("storage_provider", "local")
            file_path = analysis.diagnostics.get("file_path")
            
            if not file_path:
                return analysis

            downloader = self.storage_resolver.get_download_service(provider)
            video_data = await downloader.download_file(file_path)

            # 3. Sample frames (10%, 50%, 90%)
            timestamps = [duration * 0.1, duration * 0.5, duration * 0.9]
            visual_descriptions = []
            
            for ts in timestamps:
                try:
                    frame_bytes = await self.extractor.extract_frame(video_data, ts)
                    description = await self.analyzer.describe_frame(
                        frame_bytes, 
                        prompt="Describe what is happening in this video frame concisely."
                    )
                    timestamp_str = f"{int(ts // 60):02d}:{int(ts % 60):02d}"
                    visual_descriptions.append(f"[Visual @ {timestamp_str}]: {description}")
                except Exception as e:
                    logger.warning("visual_insight.frame_failed", timestamp=ts, error=str(e))

            if visual_descriptions:
                analysis.diagnostics["visual_context"] = visual_descriptions
                logger.info("knowledge_base.visual_insight_generated", media_id=str(analysis.media_id), count=len(visual_descriptions))
            
        except Exception as exc:
            logger.error("knowledge_base.visual_insight_failed", error=str(exc))
            
        return analysis
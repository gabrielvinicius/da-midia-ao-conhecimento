"""Implementações concretas dos passos do pipeline de análise."""
from __future__ import annotations

import inspect
import re
from typing import Any, Optional
import structlog
from src.shared.utils.text import strip_markdown
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
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
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
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if not analysis.chunks:
            return analysis
        
        sentiments_result = self.service.analyze(analysis.chunks, self.language)
        sentiments = await sentiments_result if inspect.isawaitable(sentiments_result) else sentiments_result
        analysis.sentiments = sentiments
        
        # Agregação: soma das confianças por rótulo, o que pondera pela
        # frequência. Com a média, um único trecho positivo com confiança alta
        # vencia dezenas de trechos neutros.
        if sentiments:
            totals = {label: 0.0 for label in SentimentLabel}
            for sentiment in sentiments:
                totals[sentiment.label] += float(sentiment.score)
            analysis.overall_sentiment = max(totals, key=totals.get)
            analysis.diagnostics["sentiment_distribution"] = {
                label.value: sum(1 for s in sentiments if s.label == label)
                for label in SentimentLabel
            }

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
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
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


class TopicTitleStep(AnalysisStep):
    """Gera títulos legíveis para os temas com o LLM principal.

    Faz uma única chamada para todos os temas. Se a resposta não puder ser
    interpretada, os títulos produzidos pelo BERTopic são mantidos.
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
        topics = [t for t in analysis.topics if t.id != -1]
        if not topics or not self.text_generation.is_available():
            return analysis

        blocks = []
        for t in topics:
            snippets = "\n".join(f"  - {sn}" for sn in (t.snippets or [])[:3])
            blocks.append(f"{t.id}: palavras-chave: {', '.join((t.keywords or [])[:8])}\n{snippets}")
        prompt = (
            "<<<SYSTEM>>>\nVocê dá títulos curtos e descritivos a temas extraídos de uma transcrição.\n<<<END_SYSTEM>>>\n"
            f"Para cada tema abaixo, escreva um título de no máximo {self.max_words} palavras, "
            f"em {_language_name(self.language)}, baseado apenas nas palavras-chave e nos trechos.\n"
            "Responda somente com uma linha por tema, no formato `id: título`, sem aspas nem explicações.\n\n"
            + "\n\n".join(blocks)
        )
        response = await self.text_generation.summarize_topic("Títulos dos temas", prompt, [], self.language)
        if getattr(self.text_generation, "last_call_used_fallback", False):
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


class SummarizationStep(AnalysisStep):
    def __init__(self, text_generation: TextGenerationPort, language: str, advisor: Optional[Any] = None, turbo_mode: bool = False):
        self.text_generation = text_generation
        self.language = language
        self.advisor = advisor
        self.turbo_mode = turbo_mode

    @property
    def name(self) -> str:
        return "summarization"

    async def process(self, analysis: Analysis) -> Analysis:
        if not analysis.topics:
            return analysis
            
        if self.turbo_mode:
            logger.info("pipeline.summarization_skipped_turbo_mode")
            return analysis
        
        # Intelligent Check
        if self.advisor:
            from src.shared.infrastructure.monitoring.hardware_advisor import SystemPressure
            pressure = self.advisor.recommend_strategy()
            if pressure == SystemPressure.CRITICAL:
                logger.warning("pipeline.summarization_pressure_critical_proceeding_anyway")
                # Proceed anyway for now to get results
        
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Recupera contexto visual (Level 7.0+)
        visual_context = analysis.diagnostics.get("visual_context", [])
        visual_text = "\n".join(visual_context) if visual_context else ""

        summary_parts = []
        for i, topic in enumerate(analysis.topics):
            logger.info("pipeline.summarizing_topic", topic_id=topic.id, title=topic.title, progress=f"{i+1}/{len(analysis.topics)}")
            # Injeta contexto visual se relevante para o tempo do tópico (heurística simples ou global)
            # Para Level 8.3, passamos o contexto visual global para enriquecer
            summary_md = await self._summarize_with_redundancy(topic, visual_text, analysis)
            if summary_md:
                topic.summary_md = summary_md
                topic.summary = strip_markdown(summary_md)
                summary_parts.append(summary_md)
            logger.info("pipeline.topic_summarized", topic_id=topic.id)
        
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
            "Identifique as principais teses defendidas e as evidências citadas. "
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
    """Grava trechos e embeddings no pgvector para a busca semântica."""

    def __init__(self, vector_repository: Any):
        self.vector_repo = vector_repository

    @property
    def name(self) -> str:
        return "knowledge_indexing"

    async def process(self, analysis: Analysis) -> Analysis:
        # Os embeddings são temporários: saem do diagnóstico para não irem
        # parar no JSON da análise.
        embeddings = analysis.diagnostics.pop("_temp_embeddings", None)
        if not analysis.media_id or not analysis.chunks or not embeddings:
            analysis.diagnostics["indexed_chunks"] = 0
            return analysis
        if len(embeddings) != len(analysis.chunks):
            logger.warning(
                "knowledge_indexing.size_mismatch",
                chunks=len(analysis.chunks),
                embeddings=len(embeddings),
            )

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
        await self.vector_repo.save_chunks(analysis.media_id, records)
        analysis.diagnostics["indexed_chunks"] = len(records)
        logger.info("knowledge_indexing.saved", media_id=str(analysis.media_id), count=len(records))
        return analysis


_LANGUAGE_NAMES = {
    "pt": "português do Brasil",
    "pt-br": "português do Brasil",
    "en": "inglês",
    "es": "espanhol",
}


def _language_name(language: str) -> str:
    return _LANGUAGE_NAMES.get((language or "pt").lower(), language or "português do Brasil")


class SynthesisStep(AnalysisStep):
    """Gera o resumo final da mídia com o LLM.

    Quando a transcrição cabe no contexto do modelo, ela é enviada inteira;
    caso contrário, o LLM recebe o material organizado por tema. Em ambos os
    casos, as descrições visuais dos quadros do vídeo entram como contexto.
    """

    def __init__(
        self,
        text_generation: TextGenerationPort,
        language: str,
        max_full_transcript_chars: int = 60000,
    ):
        self.text_generation = text_generation
        self.language = language
        self.max_full_transcript_chars = max_full_transcript_chars

    @property
    def name(self) -> str:
        return "synthesis"

    async def process(self, analysis: Analysis) -> Analysis:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        transcript = (analysis.document.text or "").strip() if analysis.document else ""
        if not analysis.topics and not transcript:
            return analysis

        prompt, input_mode = self.build_prompt(analysis)
        analysis.diagnostics["synthesis_input"] = input_mode

        try:
            master_summary = await self.text_generation.summarize_topic(
                "Resumo da mídia", prompt, [], self.language
            )
            used_fallback = bool(getattr(self.text_generation, "last_call_used_fallback", False))
            analysis.diagnostics["summary_source"] = "fallback" if used_fallback else "llm"
            analysis.summary = self._with_appendix(master_summary, analysis)
        except Exception as exc:
            logger.error("synthesis.failed", error=str(exc))
            analysis.diagnostics["summary_source"] = "simplified"
            analysis.summary = self._with_appendix(self._simplified_summary(analysis), analysis)
        return analysis

    @staticmethod
    def _simplified_summary(analysis: Analysis) -> str:
        """Resumo sem LLM: os temas encontrados e suas palavras-chave.

        Usado quando nem o modelo principal nem o reserva respondem. Não
        depende dos resumos por tema, que não existem no modo turbo.
        """
        lines = [
            "Não foi possível gerar o resumo com o modelo de linguagem. "
            "Estes são os temas identificados no conteúdo; os trechos de cada "
            "um estão no apêndice."
        ]
        for t in analysis.topics:
            if t.id == -1:
                continue
            keywords = ", ".join((t.keywords or [])[:6])
            line = f"- **{t.title or 'Tema'}**"
            if keywords:
                line += f" ({keywords})"
            if t.summary:
                line += f": {t.summary.splitlines()[0]}"
            lines.append(line)
        return "\n".join(lines)

    def build_prompt(self, analysis: Analysis) -> tuple[str, str]:
        """Monta o prompt e informa se usou a transcrição completa ou os temas."""
        transcript = (analysis.document.text or "").strip() if analysis.document else ""
        main_topics = [t for t in analysis.topics if t.id != -1]
        use_full = bool(transcript) and len(transcript) <= self.max_full_transcript_chars

        parts: list[str] = []
        if use_full:
            parts.append("<transcricao>\n" + transcript + "\n</transcricao>")
            if main_topics:
                overview = "\n".join(
                    f"- {t.title or 'Tema'}: {', '.join((t.keywords or [])[:6])}" for t in main_topics
                )
                parts.append("<temas_identificados>\n" + overview + "\n</temas_identificados>")
        else:
            blocks = []
            for t in main_topics:
                snippets = t.snippets or []
                body = t.summary or "\n".join(f"- {sn}" for sn in snippets[:15])
                blocks.append(
                    f"<tema id='{t.id}'>\n"
                    f"<titulo>{t.title or 'Tema'}</titulo>\n"
                    f"<palavras_chave>{', '.join((t.keywords or [])[:6])}</palavras_chave>\n"
                    f"<conteudo>\n{body}\n</conteudo>\n"
                    "</tema>"
                )
            parts.append("<temas>\n" + "\n".join(blocks) + "\n</temas>")
            noise = [sn for t in analysis.topics if t.id == -1 for sn in (t.snippets or [])[:5]]
            if noise:
                parts.append("<trechos_de_transicao>\n" + "\n".join(f"- {sn}" for sn in noise) + "\n</trechos_de_transicao>")

        visual = analysis.diagnostics.get("visual_context") or []
        if visual:
            parts.append("<descricoes_visuais>\n" + "\n".join(visual) + "\n</descricoes_visuais>")

        language = _language_name(self.language)
        system = (
            "<<<SYSTEM>>>\n"
            "Você resume aulas, palestras, reuniões e documentos com fidelidade.\n"
            "Regras:\n"
            "1. Use somente informações presentes no material; não invente fatos, números ou relações.\n"
            "2. Preserve nomes, datas, valores e termos técnicos como aparecem no material.\n"
            "3. As descrições visuais (quando houver) mostram o que aparecia na tela em alguns momentos; "
            "use-as apenas para complementar o que foi dito, sem supor o que não está descrito.\n"
            "4. Transcrições automáticas podem ter erros; se um trecho estiver confuso, não preencha a lacuna.\n"
            f"5. Escreva em {language}.\n"
            "<<<END_SYSTEM>>>"
        )
        instructions = (
            "Resuma o material abaixo.\n\n"
            "--- MATERIAL ---\n" + "\n\n".join(parts) + "\n--- FIM DO MATERIAL ---\n\n"
            "Formato da resposta (Markdown):\n"
            "# [Título específico que descreva o conteúdo]\n"
            "[Um parágrafo de visão geral, com 3 a 5 frases.]\n\n"
            "## [Título de cada assunto principal, na ordem em que aparecem]\n"
            "[Um a três parágrafos por assunto, integrando conceitos, exemplos e dados citados.]\n\n"
            "## Pontos-chave\n"
            "[Lista com 3 a 7 itens.]\n\n"
            "Não comente estas instruções na resposta."
        )
        return system + "\n" + instructions, ("full_transcript" if use_full else "topics")

    @staticmethod
    def _with_appendix(master_summary: str, analysis: Analysis) -> str:
        """Acrescenta o detalhamento por tema, para auditoria do resumo."""
        parts = []
        has_summaries = any(t.summary for t in analysis.topics if t.id != -1)
        title = "Apêndice: detalhamento por tema" if has_summaries else "Apêndice: trechos por tema"
        for t in analysis.topics:
            if t.id == -1:
                continue
            content = t.summary or "\n".join(f"> {sn}" for sn in (t.snippets or [])[:5])
            parts.append(f"### {t.title or 'Tema'}\n{content}")
        if not parts:
            return master_summary
        return f"{master_summary}\n\n---\n# {title}\n" + "\n\n".join(parts)


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

    @staticmethod
    def frame_timestamps(duration: float, seconds_per_frame: float = 180.0,
                         min_frames: int = 3, max_frames: int = 8) -> list[float]:
        """Instantes (em segundos) dos quadros a descrever."""
        if duration <= 0:
            return []
        count = max(min_frames, min(max_frames, round(duration / seconds_per_frame)))
        return [duration * (i + 0.5) / count for i in range(count)]

    async def process(self, analysis: Analysis) -> Analysis:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if not analysis.media_id or not analysis.document.segments:
            return analysis
        media_type = analysis.diagnostics.get("media_type")
        media_type = str(getattr(media_type, "value", media_type) or "").lower()
        if media_type and "video" not in media_type:
            return analysis  # áudio e documentos não têm quadros para descrever

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

            # 3. Amostragem de quadros: um a cada ~3 minutos, entre 3 e 8 quadros,
            # distribuídos uniformemente ao longo do vídeo.
            timestamps = self.frame_timestamps(duration)
            visual_descriptions = []

            for ts in timestamps:
                try:
                    frame_bytes = await self.extractor.extract_frame(video_data, ts)
                    description = await self.analyzer.describe_frame(
                        frame_bytes,
                        prompt="Describe what is happening in this video frame concisely."
                    )
                    if not description or "unavailable" in description.lower():
                        continue
                    timestamp_str = f"{int(ts // 60):02d}:{int(ts % 60):02d}"
                    visual_descriptions.append(f"[Visual @ {timestamp_str}]: {description}")
                except Exception as e:
                    logger.warning("visual_insight.frame_failed", timestamp=ts, error=str(e))

            analysis.diagnostics["visual_frames"] = len(visual_descriptions)
            if visual_descriptions:
                analysis.diagnostics["visual_context"] = visual_descriptions
                logger.info("knowledge_base.visual_insight_generated", media_id=str(analysis.media_id), count=len(visual_descriptions))

        except Exception as exc:
            logger.error("knowledge_base.visual_insight_failed", error=str(exc))

        return analysis
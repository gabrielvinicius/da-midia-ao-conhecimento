"""Etapas do pipeline de análise.

Ordem (ver pipeline_factory): trechos → sentimento → temas → indexação →
análise visual → liberação de memória → títulos dos temas → síntese →
verificação de fidelidade. As etapas que usam modelos locais (no worker)
vêm antes das que usam o modelo de linguagem (no Ollama), e a memória da GPU
é devolvida entre os dois grupos: numa placa de 12 GB não cabem todos juntos.
"""
from __future__ import annotations

import inspect
import re
from typing import Any, Optional, Sequence

import structlog

from src.media_processing.application.ports import VideoFrameExtractorPort, VisualAnalysisPort
from src.storage.application.ports import StorageServiceResolverPort
from src.text_analysis.application.pipeline.base import AnalysisStep
from src.text_analysis.application.ports import (
    ChunkingServicePort,
    EmbeddingServicePort,
    ReleasablePort,
    SentimentServicePort,
    TextGenerationPort,
    TextGenerationUnavailableError,
    TopicModelingPort,
)
from src.text_analysis.domain import Analysis, SentimentLabel
from src.text_analysis.domain.grounding import assess_grounding, split_sentences

logger = structlog.get_logger(__name__)

APPENDIX_MARKER = "\n\n---\n# Apêndice"


def _analysis_language(analysis: Analysis, default: str) -> str:
    """Idioma detectado na transcrição (para palavras vazias e sentimento)."""
    return str(analysis.diagnostics.get("language") or default or "pt")


def format_timestamp(seconds: Optional[float]) -> Optional[str]:
    if seconds is None:
        return None
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


async def _maybe_await(value):
    return await value if inspect.isawaitable(value) else value


class ChunkingStep(AnalysisStep):
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
        sentiments = await _maybe_await(self.service.analyze(analysis.chunks, language))
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
    """Calcula os vetores dos trechos (uma vez, para todo o pipeline) e os temas."""

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
        embeddings = await _maybe_await(
            self.embedding_service.embed([chunk.text for chunk in analysis.chunks])
        )
        analysis.chunk_embeddings = [e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings]

        topics, diagnostics = await self.topic_modeling.model_topics(
            analysis.chunks, embeddings, _analysis_language(analysis, self.language)
        )
        analysis.topics = topics
        analysis.diagnostics.update(diagnostics)
        return analysis


class KnowledgeIndexingStep(AnalysisStep):
    """Grava trechos e vetores no pgvector para a busca semântica."""

    def __init__(self, vector_repository: Any):
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
        await self.vector_repo.save_chunks(analysis.media_id, records)
        analysis.diagnostics["indexed_chunks"] = len(records)
        logger.info("knowledge_indexing.saved", media_id=str(analysis.media_id), count=len(records))
        return analysis


class VisualInsightStep(AnalysisStep):
    """Descreve alguns quadros do vídeo para complementar a transcrição."""

    PROMPT = (
        "Describe concisely what is shown in this video frame: any text, slide, "
        "formula, chart or diagram on screen, and what the people are doing."
    )

    def __init__(
        self,
        visual_analyzer: VisualAnalysisPort,
        frame_extractor: VideoFrameExtractorPort,
        storage_resolver: StorageServiceResolverPort,
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
        """Instantes (em segundos) dos quadros: um a cada ~3 min, entre 3 e 8."""
        if duration <= 0:
            return []
        count = max(min_frames, min(max_frames, round(duration / seconds_per_frame)))
        return [duration * (i + 0.5) / count for i in range(count)]

    async def process(self, analysis: Analysis) -> Analysis:
        segments = analysis.document.segments if analysis.document else None
        if not analysis.media_id or not segments:
            return analysis
        media_type = analysis.diagnostics.get("media_type")
        media_type = str(getattr(media_type, "value", media_type) or "").lower()
        if media_type and "video" not in media_type:
            return analysis  # áudio e documentos não têm quadros
        duration = segments[-1].get("end", 0) or 0
        file_path = analysis.diagnostics.get("file_path")
        if duration <= 0 or not file_path:
            return analysis

        try:
            provider = analysis.diagnostics.get("storage_provider", "local")
            video_data = await self.storage_resolver.get_download_service(provider).download_file(file_path)
            timestamps = self.frame_timestamps(duration)
            frames = await self.extractor.extract_frames(video_data, timestamps)

            descriptions = []
            for ts, frame in zip(timestamps, frames):
                if not frame:
                    continue
                description = await self.analyzer.describe_frame(frame, prompt=self.PROMPT)
                if description and "unavailable" not in description.lower():
                    descriptions.append(f"[{format_timestamp(ts)}] {description.strip()}")
        finally:
            # Devolve a memória da GPU antes das etapas com o modelo de linguagem.
            release = getattr(self.analyzer, "release", None)
            if release:
                try:
                    await _maybe_await(release())
                except Exception as exc:
                    logger.warning("visual_insight.release_failed", error=str(exc))

        analysis.diagnostics["visual_frames"] = len(descriptions)
        if descriptions:
            analysis.diagnostics["visual_context"] = descriptions
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


_LANGUAGE_NAMES = {
    "pt": "português do Brasil",
    "pt-br": "português do Brasil",
    "en": "inglês",
    "es": "espanhol",
}


def _language_name(language: str) -> str:
    return _LANGUAGE_NAMES.get((language or "pt").lower(), language or "português do Brasil")


class SynthesisStep(AnalysisStep):
    """Resumo final da mídia.

    - Transcrição de até ``max_full_transcript_chars``: vai inteira ao modelo.
    - Maior que isso (gravações longas): a transcrição inteira é dividida em
      blocos consecutivos; cada bloco é resumido e os resumos parciais são
      unidos numa segunda chamada. Antes, gravações longas eram resumidas a
      partir de cinco trechos por tema, e o que o BERTopic classificava como
      ruído ficava de fora.
    - Se nenhum modelo responder: resumo simplificado com os temas.
    """

    def __init__(
        self,
        text_generation: TextGenerationPort,
        language: str,
        max_full_transcript_chars: int = 36000,
        block_chars: int = 20000,
    ):
        self.text_generation = text_generation
        self.language = language
        self.max_full_transcript_chars = max_full_transcript_chars
        self.block_chars = block_chars

    @property
    def name(self) -> str:
        return "synthesis"

    async def process(self, analysis: Analysis) -> Analysis:
        transcript = (analysis.document.text or "").strip() if analysis.document else ""
        if not analysis.topics and not transcript:
            return analysis

        used_reserve = False
        try:
            if len(transcript) <= self.max_full_transcript_chars:
                analysis.diagnostics["synthesis_input"] = "full_transcript"
                prompt = self.build_prompt(analysis)
            else:
                blocks = self.split_blocks(analysis)
                analysis.diagnostics["synthesis_input"] = "sections"
                analysis.diagnostics["synthesis_sections"] = len(blocks)
                partials = []
                for index, block in enumerate(blocks, start=1):
                    partials.append(await self._generate(self.build_section_prompt(block, index, len(blocks))))
                    used_reserve = used_reserve or self.text_generation.last_used_reserve
                prompt = self.build_prompt(analysis, partials=list(zip(blocks, partials)))
            master_summary = await self._generate(prompt)
            used_reserve = used_reserve or self.text_generation.last_used_reserve
            analysis.diagnostics["summary_source"] = "reserve" if used_reserve else "llm"
            analysis.summary = self._with_appendix(master_summary, analysis)
        except Exception as exc:  # inclui TextGenerationUnavailableError
            logger.error("synthesis.failed", error=str(exc))
            analysis.diagnostics["summary_source"] = "simplified"
            analysis.summary = self._with_appendix(self._simplified_summary(analysis), analysis)
        return analysis

    async def _generate(self, prompt: str) -> str:
        return await self.text_generation.summarize_topic("Resumo da mídia", prompt, [], self.language)

    def split_blocks(self, analysis: Analysis) -> list[dict]:
        """Blocos consecutivos de até ``block_chars``, com início e fim na gravação."""
        pieces = [(c.text, c.start, c.end) for c in analysis.chunks] or [
            (analysis.document.text[i:i + 2000], None, None)
            for i in range(0, len(analysis.document.text), 2000)
        ]
        blocks: list[dict] = []
        current: list[tuple] = []
        size = 0
        for piece in pieces:
            if current and size + len(piece[0]) > self.block_chars:
                blocks.append(self._block(current))
                current, size = [], 0
            current.append(piece)
            size += len(piece[0]) + 1
        if current:
            blocks.append(self._block(current))
        return blocks

    @staticmethod
    def _block(pieces: list[tuple]) -> dict:
        return {
            "text": " ".join(p[0] for p in pieces),
            "start": next((p[1] for p in pieces if p[1] is not None), None),
            "end": next((p[2] for p in reversed(pieces) if p[2] is not None), None),
        }

    def _system(self) -> str:
        return (
            "<<<SYSTEM>>>\n"
            "Você resume aulas, palestras, reuniões e documentos com fidelidade.\n"
            "Regras:\n"
            "1. Use somente informações presentes no material; não invente fatos, números ou relações.\n"
            "2. Preserve nomes, datas, valores e termos técnicos como aparecem no material.\n"
            "3. As descrições visuais (quando houver) mostram o que aparecia na tela em alguns momentos; "
            "use-as apenas para complementar o que foi dito, sem supor o que não está descrito.\n"
            "4. Transcrições automáticas podem ter erros; se um trecho estiver confuso, não preencha a lacuna.\n"
            f"5. Escreva em {_language_name(self.language)}.\n"
            "<<<END_SYSTEM>>>"
        )

    def build_section_prompt(self, block: dict, index: int, total: int) -> str:
        span = ""
        if block.get("start") is not None and block.get("end") is not None:
            span = f", de {format_timestamp(block['start'])} a {format_timestamp(block['end'])}"
        return (
            self._system() + "\n"
            f"Este é o trecho {index} de {total} de uma transcrição{span}. "
            "Resuma somente este trecho, em uma lista de 5 a 10 itens, com os conceitos, "
            "exemplos, dados e conclusões que ele contém, na ordem em que aparecem. "
            "Não tire conclusões sobre o restante da gravação.\n\n"
            "<trecho>\n" + block["text"] + "\n</trecho>"
        )

    def build_prompt(self, analysis: Analysis, partials: Optional[list] = None) -> str:
        """Prompt final: transcrição inteira ou resumos parciais em ordem."""
        main_topics = [t for t in analysis.topics if t.id != -1]
        parts: list[str] = []
        if partials is None:
            transcript = (analysis.document.text or "").strip()
            parts.append("<transcricao>\n" + transcript + "\n</transcricao>")
        else:
            sections = []
            for i, (block, text) in enumerate(partials, start=1):
                span = ""
                if block.get("start") is not None and block.get("end") is not None:
                    span = f" ({format_timestamp(block['start'])}–{format_timestamp(block['end'])})"
                sections.append(f"<parte n='{i}'{span}>\n{text}\n</parte>")
            parts.append(
                "<resumos_parciais>\nResumos de partes consecutivas da gravação, em ordem:\n"
                + "\n".join(sections) + "\n</resumos_parciais>"
            )
        if main_topics:
            overview = "\n".join(f"- {t.title or 'Tema'}: {', '.join((t.keywords or [])[:6])}" for t in main_topics)
            parts.append("<temas_identificados>\n" + overview + "\n</temas_identificados>")
        visual = analysis.diagnostics.get("visual_context") or []
        if visual:
            parts.append("<descricoes_visuais>\n" + "\n".join(visual) + "\n</descricoes_visuais>")

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
        return self._system() + "\n" + instructions

    @staticmethod
    def _simplified_summary(analysis: Analysis) -> str:
        """Resumo sem modelo de linguagem: os temas e suas palavras-chave."""
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
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _with_appendix(master_summary: str, analysis: Analysis) -> str:
        """Apêndice para conferência: trechos representativos de cada tema,
        com o momento da gravação, e o que foi descrito da tela."""
        starts = {chunk.text: chunk.start for chunk in analysis.chunks}
        parts = []
        for t in analysis.topics:
            if t.id == -1:
                continue
            lines = []
            for snippet in (t.snippets or [])[:5]:
                stamp = format_timestamp(starts.get(snippet))
                lines.append(f"> {'[' + stamp + '] ' if stamp else ''}{snippet}")
            parts.append(f"### {t.title or 'Tema'}\n" + "\n>\n".join(lines))
        visual = analysis.diagnostics.get("visual_context") or []
        if visual:
            parts.append(
                "### O que aparecia na tela\n"
                "_Descrições automáticas de alguns quadros do vídeo (em inglês), usadas como contexto._\n\n"
                + "\n".join(f"- {v}" for v in visual)
            )
        if not parts:
            return master_summary
        return master_summary + APPENDIX_MARKER + ": trechos por tema\n" + "\n\n".join(parts)


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
        if analysis.diagnostics.get("summary_source") == "simplified":
            return analysis  # montado dos próprios temas: não há o que verificar
        body = analysis.summary.split(APPENDIX_MARKER, 1)[0]
        sentences = split_sentences(body)
        if not sentences:
            return analysis

        passages = analysis.chunk_embeddings
        if len(passages) != len(analysis.chunks):
            passages = await _maybe_await(self.embedding_service.embed([c.text for c in analysis.chunks]))
        queries = await _maybe_await(self.embedding_service.embed(sentences, kind="query"))
        report = assess_grounding(
            sentences, queries, passages, [c.start for c in analysis.chunks], self.threshold
        )
        analysis.diagnostics["grounding"] = report.to_dict()
        return analysis

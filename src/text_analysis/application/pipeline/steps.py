"""Etapas do pipeline de análise.

Ordem (ver pipeline_factory): trechos → sentimento → temas → indexação →
liberação de memória → títulos dos temas → síntese → verificação de
fidelidade. As descrições dos quadros de vídeo chegam prontas, com a
transcrição (media_processing), em diagnostics["visual_context"].

As etapas que usam modelos locais (no worker) vêm antes das que usam o modelo
de linguagem (no Ollama), e a memória da GPU é devolvida entre os dois grupos:
numa placa de 12 GB não cabem todos juntos.
"""
from __future__ import annotations

import inspect
import math
import re
from typing import Any, Optional, Sequence

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


# Tamanho do resumo, proporcional à transcrição: cerca de 12% das palavras,
# entre 120 e 900. Abaixo de 200 palavras, formato curto (sem seções): um
# resumo com título, seções e pontos-chave ficava do tamanho de uma fala curta.
SUMMARY_RATIO = 0.12
SUMMARY_MIN_WORDS = 120
SUMMARY_MAX_WORDS = 900
SHORT_SUMMARY_WORDS = 200
# Teto da resposta em tokens: no Qwen, o português gasta ~1,8 token por
# palavra; a margem cobre títulos e marcação.
TOKENS_PER_WORD = 2.2
TOKEN_MARGIN = 150


def summary_target_words(source_words: int) -> int:
    return max(SUMMARY_MIN_WORDS, min(SUMMARY_MAX_WORDS, round(source_words * SUMMARY_RATIO)))


def response_token_cap(words: int) -> int:
    return int(words * TOKENS_PER_WORD) + TOKEN_MARGIN


class SynthesisStep(AnalysisStep):
    """Resumo final da mídia.

    - Transcrição de até ``max_full_transcript_chars``: vai inteira ao modelo.
    - Maior que isso (gravações longas): a transcrição inteira é dividida em
      blocos consecutivos; cada bloco é resumido e os resumos parciais são
      unidos numa segunda chamada.
    - O tamanho pedido acompanha o tamanho do material (``summary_target_words``),
      e a resposta tem teto de tokens.
    - Se nenhum modelo responder: resumo simplificado com os temas.

    Os limites vêm de medições com o tokenizador do Qwen (~3,5 caracteres por
    token em português falado): 36 mil caracteres com temas e quadros somam
    ~11,2 mil tokens, o que deixa espaço para a resposta na janela de 16.384.
    Os blocos usam o mesmo limite; com 20 mil, cada um ocupava só 35% da janela
    e uma aula de duas horas pedia sete chamadas em vez de quatro.
    """

    def __init__(
        self,
        text_generation: TextGenerationPort,
        language: str,
        max_full_transcript_chars: int = 36000,
        block_chars: int = 36000,
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

        target = summary_target_words(len(transcript.split()))
        analysis.diagnostics["synthesis_target_words"] = target
        self._used_reserve = False
        self._prompt_tokens: list[int] = []
        self._truncated = False
        try:
            if len(transcript) <= self.max_full_transcript_chars:
                analysis.diagnostics["synthesis_input"] = "full_transcript"
                prompt = self.build_prompt(analysis, target_words=target)
            else:
                blocks = self.split_blocks(analysis)
                analysis.diagnostics["synthesis_input"] = "sections"
                analysis.diagnostics["synthesis_sections"] = len(blocks)
                partials = []
                for index, block in enumerate(blocks, start=1):
                    items = self.items_for(block["text"])
                    partials.append(
                        await self._generate(
                            self.build_section_prompt(block, index, len(blocks), analysis, items),
                            max_tokens=response_token_cap(items * 30),
                        )
                    )
                prompt = self.build_prompt(analysis, partials=list(zip(blocks, partials)), target_words=target)
            master_summary = await self._generate(prompt, max_tokens=response_token_cap(target))
            analysis.diagnostics["summary_source"] = "reserve" if self._used_reserve else "llm"
            analysis.summary = self._with_appendix(master_summary, analysis)
        except Exception as exc:  # inclui TextGenerationUnavailableError
            logger.error("synthesis.failed", error=str(exc))
            analysis.diagnostics["summary_source"] = "simplified"
            analysis.summary = self._with_appendix(self._simplified_summary(analysis), analysis)
        if self._prompt_tokens:
            analysis.diagnostics["synthesis_prompt_tokens"] = max(self._prompt_tokens)
        if self._truncated:
            analysis.diagnostics["synthesis_prompt_truncated"] = True
        return analysis

    async def _generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        text = await self.text_generation.summarize_topic(
            "Resumo da mídia", prompt, [], self.language, max_tokens=max_tokens
        )
        self._used_reserve = self._used_reserve or self.text_generation.last_used_reserve is True
        tokens = getattr(self.text_generation, "last_prompt_tokens", None)
        if isinstance(tokens, int):
            self._prompt_tokens.append(tokens)
        self._truncated = self._truncated or getattr(self.text_generation, "last_prompt_truncated", False) is True
        return text

    @staticmethod
    def items_for(text: str) -> int:
        """Itens do resumo de um bloco: um a cada ~2.500 caracteres, entre 5 e 15."""
        return max(5, min(15, len(text) // 2500))

    @staticmethod
    def _is_document(analysis: Analysis) -> bool:
        """Sem horário em nenhum trecho, o material é um documento (PDF, OCR)."""
        return not any(getattr(c, "start", None) is not None for c in analysis.chunks or [])

    def split_blocks(self, analysis: Analysis) -> list[dict]:
        """Blocos consecutivos de até ``block_chars``.

        Gravação: junta os trechos, com início e fim na gravação. Documento: os
        trechos de documentos se sobrepõem (para a busca), então o texto é
        dividido direto, por frases, sem repetir nada.
        """
        if self._is_document(analysis):
            sentences = [s for s in re.split(r"(?<=[.!?])\s+", analysis.document.text or "") if s.strip()]
            pieces = [(s, None, None) for s in sentences]
        else:
            pieces = [(c.text, c.start, c.end) for c in analysis.chunks]
        # Blocos de tamanho parecido: com o limite puro, 110 mil caracteres
        # davam três blocos cheios e um de 2 mil, resumido com o mesmo peso.
        total = sum(len(p[0]) + 1 for p in pieces)
        target = total / max(1, math.ceil(total / self.block_chars))
        blocks: list[dict] = []
        current: list[tuple] = []
        size = 0
        for piece in pieces:
            if current and (size >= target or size + len(piece[0]) > self.block_chars):
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

    def build_section_prompt(
        self, block: dict, index: int, total: int, analysis: Optional[Analysis] = None, items: int = 8
    ) -> str:
        kind = "um documento" if analysis is not None and self._is_document(analysis) else "uma transcrição"
        span = ""
        if block.get("start") is not None and block.get("end") is not None:
            span = f", de {format_timestamp(block['start'])} a {format_timestamp(block['end'])}"
        return (
            self._system() + "\n"
            f"Este é o trecho {index} de {total} de {kind}{span}. "
            f"Resuma somente este trecho, em uma lista de até {items} itens, com os conceitos, "
            "exemplos, dados e conclusões que ele contém, na ordem em que aparecem. "
            "Não tire conclusões sobre o restante do material.\n\n"
            "<trecho>\n" + block["text"] + "\n</trecho>"
        )

    def build_prompt(
        self, analysis: Analysis, partials: Optional[list] = None, target_words: Optional[int] = None
    ) -> str:
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
                "<resumos_parciais>\nResumos de partes consecutivas do material, em ordem:\n"
                + "\n".join(sections) + "\n</resumos_parciais>"
            )
        if main_topics:
            overview = "\n".join(f"- {t.title or 'Tema'}: {', '.join((t.keywords or [])[:6])}" for t in main_topics)
            parts.append("<temas_identificados>\n" + overview + "\n</temas_identificados>")
        visual = analysis.diagnostics.get("visual_context") or []
        if visual:
            parts.append("<descricoes_visuais>\n" + "\n".join(visual) + "\n</descricoes_visuais>")

        target = target_words or SUMMARY_MAX_WORDS
        if target <= SHORT_SUMMARY_WORDS:
            response_format = (
                f"Formato da resposta (Markdown), com cerca de {target} palavras no total:\n"
                "# [Título específico que descreva o conteúdo]\n"
                "[Um ou dois parágrafos com o essencial.]\n\n"
                "## Pontos-chave\n"
                "[Lista com até 3 itens.]\n\n"
            )
        else:
            response_format = (
                f"Formato da resposta (Markdown), com cerca de {target} palavras no total:\n"
                "# [Título específico que descreva o conteúdo]\n"
                "[Um parágrafo de visão geral.]\n\n"
                "## [Título de cada assunto principal, na ordem em que aparecem]\n"
                "[Parágrafos que integrem conceitos, exemplos e dados citados.]\n\n"
                "## Pontos-chave\n"
                "[Lista com 3 a 7 itens.]\n\n"
            )
        instructions = (
            "Resuma o material abaixo.\n\n"
            "--- MATERIAL ---\n" + "\n\n".join(parts) + "\n--- FIM DO MATERIAL ---\n\n"
            + response_format
            + "Não comente estas instruções na resposta."
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

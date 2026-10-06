"""Síntese: o resumo final da mídia, montado pelo modelo de linguagem.

As regras sobre o conteúdo (tamanho do resumo, peso e tom dos temas) estão em
``domain.content_profile``; aqui fica como elas viram prompt e texto.
"""
from __future__ import annotations

import math
import re
from typing import Optional, Sequence

import structlog

from src.shared.domain.time.timestamps import format_timestamp
from src.text_analysis.application.pipeline.base import AnalysisStep
from src.text_analysis.application.ports import TextGenerationPort
from src.text_analysis.domain import Analysis, SentimentLabel, SummarySource
from src.text_analysis.domain.content_profile import (
    SUMMARY_MAX_WORDS,
    Tone,
    chunk_tones,
    is_short_summary,
    main_topics,
    predominant_tone,
    summary_target_words,
    topic_profiles,
)

logger = structlog.get_logger(__name__)

APPENDIX_MARKER = "\n\n---\n# Apêndice"

# Teto da resposta em tokens: no Qwen, o português gasta ~1,8 token por
# palavra; a margem cobre títulos e marcação.
TOKENS_PER_WORD = 2.2
TOKEN_MARGIN = 150

_LANGUAGE_NAMES = {
    "pt": "português do Brasil",
    "pt-br": "português do Brasil",
    "en": "inglês",
    "es": "espanhol",
}

_TONE_NAMES = {
    SentimentLabel.POSITIVE: "positivo",
    SentimentLabel.NEGATIVE: "negativo",
    SentimentLabel.NEUTRAL: "neutro",
}


def language_name(language: str) -> str:
    return _LANGUAGE_NAMES.get((language or "pt").lower(), language or "português do Brasil")


def response_token_cap(words: int) -> int:
    return int(words * TOKENS_PER_WORD) + TOKEN_MARGIN


def tone_text(tone: Optional[Tone]) -> Optional[str]:
    if tone is None:
        return None
    if tone.label is None:
        return f"misto ({tone.total} trechos)"
    return f"{_TONE_NAMES[tone.label]} ({tone.count} de {tone.total} trechos)"


def describe_tone(labels: Sequence[SentimentLabel]) -> Optional[str]:
    """Tom de um conjunto de trechos, como o modelo de sentimento o classificou."""
    return tone_text(predominant_tone(labels))


def topic_overview(analysis: Analysis) -> tuple[list[str], bool]:
    """Linhas dos temas para o prompt e se os pesos estão disponíveis."""

    def keywords(topic) -> str:
        return ", ".join((topic.keywords or [])[:6])

    profiles = topic_profiles(analysis.topics, analysis.chunks or [], analysis.sentiments or [])
    if profiles is None:
        return [f"- {t.title or 'Tema'}: {keywords(t)}" for t in main_topics(analysis.topics)], False
    lines = []
    for p in profiles:
        where = f", a partir de {format_timestamp(p.start)}" if p.start is not None else ""
        tone = tone_text(p.tone)
        tone = f"; tom: {tone}" if tone else ""
        lines.append(f"- {p.topic.title or 'Tema'} ({keywords(p.topic)}): {p.share_percent}% do conteúdo{where}{tone}")
    return lines, True


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

    required = True

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
            analysis.summary_source = SummarySource.RESERVE if self._used_reserve else SummarySource.LLM
            analysis.summary = self._with_appendix(master_summary, analysis)
        except Exception as exc:  # inclui TextGenerationUnavailableError
            logger.error("synthesis.failed", error=str(exc))
            analysis.summary_source = SummarySource.SIMPLIFIED
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
            "5. O tom (quando houver) foi classificado automaticamente por trecho. Mencione-o só se for "
            "positivo ou negativo de forma predominante, e sem atribuir emoções ou intenções que não foram ditas.\n"
            f"6. Escreva em {language_name(self.language)}.\n"
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
        topic_lines, weighted = topic_overview(analysis)
        if topic_lines:
            parts.append("<temas_identificados>\n" + "\n".join(topic_lines) + "\n</temas_identificados>")
        overall_tone = describe_tone(list(chunk_tones(analysis.chunks or [], analysis.sentiments or []).values()))
        if overall_tone:
            parts.append("<tom_geral>\n" + overall_tone + "\n</tom_geral>")
        visual = analysis.visual_context
        if visual:
            parts.append("<descricoes_visuais>\n" + "\n".join(visual) + "\n</descricoes_visuais>")

        target = target_words or SUMMARY_MAX_WORDS
        if is_short_summary(target):
            response_format = (
                f"Formato da resposta (Markdown), com cerca de {target} palavras no total:\n"
                "# [Título específico que descreva o conteúdo]\n"
                "[Um ou dois parágrafos com o essencial.]\n\n"
                "## Pontos-chave\n"
                "[Lista com até 3 itens.]\n\n"
            )
        else:
            timed = weighted and not self._is_document(analysis)
            heading = "## [Título de cada assunto principal, na ordem em que aparecem"
            heading += " (momento em que começa, como na lista de temas)]\n" if timed else "]\n"
            weights = (
                "Os temas identificados estão na ordem em que aparecem, com a parcela do "
                "conteúdo de cada um: dê a cada assunto espaço proporcional a essa parcela.\n"
                if weighted else ""
            )
            response_format = (
                weights
                + f"Formato da resposta (Markdown), com cerca de {target} palavras no total:\n"
                "# [Título específico que descreva o conteúdo]\n"
                "[Um parágrafo de visão geral.]\n\n"
                + heading
                + "[Parágrafos que integrem conceitos, exemplos e dados citados.]\n\n"
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
        # Na ordem em que os temas aparecem, como as seções do resumo.
        ordered = sorted(analysis.topics, key=lambda t: min(t.chunk_indices) if t.chunk_indices else 0)
        for t in ordered:
            if t.id == -1:
                continue
            lines = []
            for snippet in (t.snippets or [])[:5]:
                stamp = format_timestamp(starts.get(snippet))
                lines.append(f"> {'[' + stamp + '] ' if stamp else ''}{snippet}")
            parts.append(f"### {t.title or 'Tema'}\n" + "\n>\n".join(lines))
        visual = analysis.visual_context
        if visual:
            parts.append(
                "### O que aparecia na tela\n"
                "_Descrições automáticas de alguns quadros do vídeo (em inglês), usadas como contexto._\n\n"
                + "\n".join(f"- {v}" for v in visual)
            )
        if not parts:
            return master_summary
        return master_summary + APPENDIX_MARKER + ": trechos por tema\n" + "\n\n".join(parts)

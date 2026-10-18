"""Capítulos e perguntas de revisão: ajudam a navegar e a estudar a mídia.

Medido numa aula de 30 min (Qwen3.5-9B, RTX 3060): os títulos dos capítulos
custam uma chamada curta; as perguntas, uma chamada de ~20–30 s. Quando o
modelo era quem dizia os horários, errava (capítulos até "17:30" numa aula de
30 min); por isso os cortes vêm dos temas e as perguntas apontam o número do
capítulo, que o sistema converte no horário.
"""
from __future__ import annotations

import re
from typing import Optional

import structlog

from src.shared.domain.time.timestamps import format_timestamp
from src.text_analysis.application.pipeline.base import AnalysisStep
from src.text_analysis.application.pipeline.synthesis import APPENDIX_MARKER, language_name
from src.text_analysis.application.ports import TextGenerationPort, TextGenerationUnavailableError
from src.text_analysis.domain import Analysis
from src.text_analysis.domain.chapters import Chapter, ChapterRules, ReviewQuestion, chapter_spans

logger = structlog.get_logger(__name__)

CHAPTER_SAMPLE_CHARS = 600  # começo de cada capítulo, para o título
_TITLE_LINE = re.compile(r"^\s*[-*]?\s*(\d+)\s*[:.)\-–]\s*(.+?)\s*$")
_QUESTION_LINE = re.compile(
    r"^\s*(?:\d+[.)]\s*)?P:\s*(?P<q>.+?)\s*\|\s*R:\s*(?P<a>.+?)\s*(?:\|\s*C:\s*(?P<c>\d+))?\s*$",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    return text.strip().strip('"\'`*').strip()


class ChapterStep(AnalysisStep):
    """Capítulos com horário: cortes pelos temas, títulos numa chamada só."""

    def __init__(
        self,
        text_generation: TextGenerationPort,
        language: str,
        max_words: int = 8,
        rules: ChapterRules = ChapterRules(),
    ):
        self.text_generation = text_generation
        self.language = language
        self.max_words = max_words
        self.rules = rules

    @property
    def name(self) -> str:
        return "chapters"

    async def process(self, analysis: Analysis) -> Analysis:
        spans = chapter_spans(analysis.chunks or [], analysis.topics or [], self.rules)
        if not spans:
            return analysis  # documento, gravação curta ou sem horários
        titles: dict[int, str] = {}
        unavailable: Optional[TextGenerationUnavailableError] = None
        try:
            titles = self.parse_titles(
                await self.text_generation.summarize_topic(
                    "Capítulos", self.build_prompt(analysis, spans), [], self.language
                )
            )
        except TextGenerationUnavailableError as exc:
            unavailable = exc
        chunks = analysis.chunks
        analysis.chapters = [
            Chapter(
                start=float(chunks[a].start or 0.0),
                end=float(chunks[b].end or chunks[b].start or 0.0),
                title=titles.get(n) or f"Parte {n}",
                first_chunk=a,
                last_chunk=b,
            )
            for n, (a, b) in enumerate(spans, start=1)
        ]
        if unavailable is not None:
            # Os cortes valem sem o modelo ("Parte n"), mas a etapa fica
            # registrada como falha, em vez de sair "ok" sem os títulos.
            raise unavailable
        return analysis

    def build_prompt(self, analysis: Analysis, spans: list[tuple[int, int]]) -> str:
        blocks = []
        for n, (a, b) in enumerate(spans, start=1):
            text = " ".join(c.text for c in analysis.chunks[a:b + 1])[:CHAPTER_SAMPLE_CHARS]
            start = format_timestamp(analysis.chunks[a].start)
            blocks.append(f"{n} ({start}): {text}")
        return (
            "<<<SYSTEM>>>\nVocê dá títulos curtos e descritivos às partes de uma gravação.\n<<<END_SYSTEM>>>\n"
            f"Para cada parte abaixo (o início do que é dito nela), escreva um título de no máximo "
            f"{self.max_words} palavras, em {language_name(self.language)}, que diga o assunto da parte. "
            "Responda só com uma linha por parte, no formato `número: título`.\n\n" + "\n\n".join(blocks)
        )

    def parse_titles(self, text: Optional[str]) -> dict[int, str]:
        titles = {}
        for line in (text or "").splitlines():
            match = _TITLE_LINE.match(line)
            if match and _clean(match.group(2)):
                words = _clean(match.group(2)).split()
                titles[int(match.group(1))] = " ".join(words[: self.max_words + 4])
        return titles


class ReviewQuestionsStep(AnalysisStep):
    """Perguntas de revisão com resposta e o momento da gravação onde ela está."""

    def __init__(self, text_generation: TextGenerationPort, language: str, max_transcript_chars: int = 18000):
        self.text_generation = text_generation
        self.language = language
        # Acima disso, as perguntas partem do resumo (ANALYSIS_FULL_TRANSCRIPT_CHARS).
        self.max_transcript_chars = max_transcript_chars

    @property
    def name(self) -> str:
        return "review_questions"

    async def process(self, analysis: Analysis) -> Analysis:
        material = self.material(analysis)
        if not material:
            return analysis
        count = self.count_for(analysis)
        answer = await self.text_generation.summarize_topic(
            "Perguntas de revisão", self.build_prompt(analysis, material, count), [], self.language
        )
        analysis.review_questions = self.parse(answer, analysis)[:count]
        return analysis

    @staticmethod
    def count_for(analysis: Analysis) -> int:
        """De 3 a 8 perguntas, uma por capítulo (ou por ~5 min sem capítulos)."""
        if analysis.chapters:
            return max(3, min(8, len(analysis.chapters)))
        words = len((analysis.document.text or "").split()) if analysis.document else 0
        return max(3, min(8, words // 700))

    def material(self, analysis: Analysis) -> Optional[str]:
        """A transcrição, se couber; senão, o resumo (sem o apêndice)."""
        text = (analysis.document.text or "").strip() if analysis.document else ""
        if text and len(text) <= self.max_transcript_chars:
            return text
        summary = (analysis.summary or "").split(APPENDIX_MARKER, 1)[0].strip()
        return summary or None

    def build_prompt(self, analysis: Analysis, material: str, count: int) -> str:
        chapters = ""
        if analysis.chapters:
            chapters = "<capitulos>\n" + "\n".join(
                f"{n}. {c.title} ({format_timestamp(c.start)})" for n, c in enumerate(analysis.chapters, start=1)
            ) + "\n</capitulos>\n\n"
        where = " | C: número do capítulo onde a resposta está" if analysis.chapters else ""
        return (
            "<<<SYSTEM>>>\nVocê prepara perguntas de revisão para estudantes, fiéis ao material.\n<<<END_SYSTEM>>>\n"
            f"Com base só no material abaixo, escreva {count} perguntas de revisão em "
            f"{language_name(self.language)}, misturando perguntas de lembrar fatos e de compreender ideias, "
            "cada uma com a resposta curta tirada do material. Não use conhecimento de fora.\n"
            f"Uma linha por pergunta, no formato `P: pergunta | R: resposta{where}`, sem comentários.\n\n"
            + chapters + "<material>\n" + material + "\n</material>"
        )

    @staticmethod
    def parse(text: Optional[str], analysis: Analysis) -> list[ReviewQuestion]:
        questions = []
        for line in (text or "").splitlines():
            match = _QUESTION_LINE.match(line)
            if not match:
                continue
            chapter = int(match.group("c")) if match.group("c") else None
            start = None
            if chapter and 1 <= chapter <= len(analysis.chapters):
                start = analysis.chapters[chapter - 1].start
            questions.append(ReviewQuestion(question=_clean(match.group("q")), answer=_clean(match.group("a")), start=start))
        return questions


__all__ = ["ChapterStep", "ReviewQuestionsStep"]

"""Capítulos e perguntas de revisão de uma gravação.

Os cortes dos capítulos vêm dos dados, não do modelo de linguagem: num teste
com uma aula de 30 min, pedir ao modelo os horários deu capítulos até
"17:30" e nenhum para a pandemia nem para a conclusão. Aqui, cada capítulo é
uma sequência de trechos do mesmo tema; o modelo só dá os títulos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from src.text_analysis.domain.content_profile import OUTLIER_TOPIC_ID
from src.text_analysis.domain.entities.sentiment import TextChunk
from src.text_analysis.domain.entities.topic import Topic


@dataclass(frozen=True)
class ChapterRules:
    """Limites dos capítulos; vêm das configurações (CHAPTERS_*)."""

    min_recording_seconds: float = 4 * 60  # gravações curtas não precisam de capítulos
    min_chapter_seconds: float = 2 * 60
    max_chapters: int = 10
    seconds_per_chapter: float = 5 * 60  # sem temas: um capítulo a cada ~5 min

    def __post_init__(self) -> None:
        if self.max_chapters < 2 or self.seconds_per_chapter <= 0:
            raise ValueError("CHAPTERS_MAX precisa ser 2 ou mais e CHAPTERS_EVERY_MINUTES, positivo")


@dataclass(frozen=True)
class Chapter:
    start: float
    end: float
    title: str
    first_chunk: int = 0  # índices dos trechos, para montar o prompt
    last_chunk: int = 0


@dataclass(frozen=True)
class ReviewQuestion:
    question: str
    answer: str
    start: Optional[float] = None  # momento da gravação onde está a resposta


def chapter_spans(
    chunks: Sequence[TextChunk], topics: Sequence[Topic], rules: ChapterRules = ChapterRules()
) -> list[tuple[int, int]]:
    """Faixas de trechos (início, fim inclusivos) de cada capítulo, em ordem.

    Sequências de trechos do mesmo tema viram capítulos; as curtas demais e as
    sem tema se juntam à anterior; acima do máximo, as vizinhas mais curtas se
    juntam. Sem temas que dividam a gravação, cortes a intervalos regulares.
    """
    if not _timed(chunks) or _duration(chunks) < rules.min_recording_seconds:
        return []
    spans = _topic_runs(chunks, topics)
    spans = _merge_short(spans, chunks, rules.min_chapter_seconds)
    if len(spans) < 2:
        spans = _even_spans(chunks, rules)
    while len(spans) > rules.max_chapters:
        spans = _merge_shortest_pair(spans, chunks)
    return spans


def _timed(chunks: Sequence[TextChunk]) -> bool:
    return bool(chunks) and all(c.start is not None for c in chunks)


def _duration(chunks: Sequence[TextChunk]) -> float:
    return float(chunks[-1].end or chunks[-1].start or 0.0)


def _span_seconds(span: tuple[int, int], chunks: Sequence[TextChunk]) -> float:
    first, last = span
    return float((chunks[last].end or chunks[last].start or 0.0) - (chunks[first].start or 0.0))


def _topic_runs(chunks: Sequence[TextChunk], topics: Sequence[Topic]) -> list[tuple[int, int]]:
    label = {i: t.id for t in topics if t.id != OUTLIER_TOPIC_ID for i in (t.chunk_indices or [])}
    runs: list[list[int]] = []
    previous = None
    for i in range(len(chunks)):
        current = label.get(i, previous)  # trecho sem tema segue o anterior
        if runs and current == previous:
            runs[-1][1] = i
        else:
            runs.append([i, i])
        previous = current
    return [(a, b) for a, b in runs]


def _merge_short(
    spans: list[tuple[int, int]], chunks: Sequence[TextChunk], min_seconds: float
) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for span in spans:
        if merged and _span_seconds(span, chunks) < min_seconds:
            merged[-1] = (merged[-1][0], span[1])
        else:
            merged.append(span)
    # O primeiro capítulo curto se junta ao seguinte.
    if len(merged) > 1 and _span_seconds(merged[0], chunks) < min_seconds:
        merged[1] = (merged[0][0], merged[1][1])
        merged.pop(0)
    return merged


def _merge_shortest_pair(spans: list[tuple[int, int]], chunks: Sequence[TextChunk]) -> list[tuple[int, int]]:
    i = min(
        range(len(spans) - 1),
        key=lambda k: _span_seconds((spans[k][0], spans[k + 1][1]), chunks),
    )
    return spans[:i] + [(spans[i][0], spans[i + 1][1])] + spans[i + 2:]


def _even_spans(chunks: Sequence[TextChunk], rules: ChapterRules) -> list[tuple[int, int]]:
    count = max(2, min(rules.max_chapters, round(_duration(chunks) / rules.seconds_per_chapter)))
    width = _duration(chunks) / count
    spans: list[tuple[int, int]] = []
    for i, chunk in enumerate(chunks):
        slot = min(int((chunk.start or 0.0) // width), count - 1)
        if spans and len(spans) - 1 == slot:
            spans[-1] = (spans[-1][0], i)
        else:
            spans.append((i, i))
    return spans


__all__ = ["Chapter", "ChapterRules", "ReviewQuestion", "chapter_spans"]

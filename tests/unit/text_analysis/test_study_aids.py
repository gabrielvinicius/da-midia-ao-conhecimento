"""Capítulos (cortes pelos temas) e perguntas de revisão."""
from unittest.mock import AsyncMock

import pytest

from src.text_analysis.application.mappers import analysis_diagnostics, restore_from_diagnostics
from src.text_analysis.application.pipeline.study import ChapterStep, ReviewQuestionsStep
from src.text_analysis.domain import Analysis, Document, TextChunk, Topic
from src.text_analysis.domain.chapters import Chapter, chapter_spans


def _chunks(n, seconds=60.0):
    return [TextChunk(id=str(i), text=f"trecho {i}. Assunto do minuto {i}.", start=i * seconds, end=(i + 1) * seconds) for i in range(n)]


def test_chapters_follow_the_topics_along_the_recording():
    """30 min: três temas em sequência viram três capítulos, com os horários
    dos próprios trechos (o modelo errava os horários)."""
    chunks = _chunks(30)
    topics = [
        Topic(id=0, keywords=[], chunk_indices=list(range(0, 10))),
        Topic(id=1, keywords=[], chunk_indices=list(range(10, 22))),
        Topic(id=2, keywords=[], chunk_indices=list(range(22, 30))),
    ]
    assert chapter_spans(chunks, topics) == [(0, 9), (10, 21), (22, 29)]


def test_short_runs_and_chunks_without_topic_join_the_previous_chapter():
    chunks = _chunks(20)
    topics = [
        Topic(id=0, keywords=[], chunk_indices=list(range(0, 8)) + [9]),  # 8 sem tema, 9 de volta ao 0
        Topic(id=1, keywords=[], chunk_indices=list(range(10, 20)) + [15]),
        Topic(id=-1, keywords=[], chunk_indices=[8]),
    ]
    assert chapter_spans(chunks, topics) == [(0, 9), (10, 19)]


def test_without_topics_chapters_come_every_five_minutes_and_short_media_get_none():
    assert chapter_spans(_chunks(30), []) == [(0, 4), (5, 9), (10, 14), (15, 19), (20, 24), (25, 29)]
    assert chapter_spans(_chunks(3), []) == []  # 3 min
    document = [TextChunk(id="a", text="texto", start=None)]
    assert chapter_spans(document, []) == []


def _gen(reply):
    gen = AsyncMock()
    gen.summarize_topic.return_value = reply
    gen.last_used_reserve = False
    return gen


@pytest.mark.asyncio
async def test_chapter_step_titles_each_part_in_one_call():
    analysis = Analysis.new(Document.from_payload("t", []))
    analysis.chunks = _chunks(30)
    analysis.topics = [Topic(id=0, keywords=[], chunk_indices=list(range(15))), Topic(id=1, keywords=[], chunk_indices=list(range(15, 30)))]
    gen = _gen("1: A crise do software\n2: \"A era da IA generativa\"")

    await ChapterStep(gen, language="pt").process(analysis)

    assert gen.summarize_topic.await_count == 1
    assert [(c.start, c.end, c.title) for c in analysis.chapters] == [
        (0.0, 900.0, "A crise do software"),
        (900.0, 1800.0, "A era da IA generativa"),
    ]
    assert "2 (15:00)" in gen.summarize_topic.call_args.args[1]


@pytest.mark.asyncio
async def test_questions_point_to_the_chapter_and_get_its_time():
    analysis = Analysis.new(Document.from_payload("O manifesto ágil teve 17 autores. " * 30, []))
    analysis.chapters = [Chapter(0.0, 600.0, "Origens"), Chapter(600.0, 1200.0, "Manifesto ágil"), Chapter(1200.0, 1800.0, "IA")]
    gen = _gen(
        "1. P: Quantos autores teve o manifesto ágil? | R: 17 desenvolvedores. | C: 2\n"
        "comentário que não segue o formato\n"
        "P: O que é vibe coding? | R: Programar sem pensar. | C: 9\n"
    )

    await ReviewQuestionsStep(gen, language="pt").process(analysis)

    prompt = gen.summarize_topic.call_args.args[1]
    assert "Escreva 3".lower() in prompt.lower() and "2. Manifesto ágil (10:00)" in prompt
    assert [(q.question, q.answer, q.start) for q in analysis.review_questions] == [
        ("Quantos autores teve o manifesto ágil?", "17 desenvolvedores.", 600.0),
        ("O que é vibe coding?", "Programar sem pensar.", None),  # capítulo inexistente: sem horário
    ]

    data = analysis_diagnostics(analysis)
    restored = Analysis.new(Document.from_payload("t", []))
    restore_from_diagnostics(restored, data)
    assert restored.review_questions == analysis.review_questions
    assert [(c.start, c.title) for c in restored.chapters] == [(c.start, c.title) for c in analysis.chapters]

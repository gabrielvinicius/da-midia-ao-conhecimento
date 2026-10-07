"""Gênero do conteúdo: identificado antes do resumo e usado no prompt."""
from unittest.mock import AsyncMock

import pytest

from src.text_analysis.application.mappers import analysis_diagnostics, restore_from_diagnostics
from src.text_analysis.application.pipeline.genre import ContentGenreStep
from src.text_analysis.application.pipeline.synthesis import SynthesisStep
from src.text_analysis.application.ports import TextGenerationUnavailableError
from src.text_analysis.domain import Analysis, ContentGenre, Document, TextChunk
from src.text_analysis.domain.content_genre import parse_genre


def test_parse_genre_reads_the_first_known_genre_without_accents():
    assert parse_genre("Opinião") is ContentGenre.OPINION
    assert parse_genre("  reunião.") is ContentGenre.MEETING
    assert parse_genre("Gênero: aula (com exemplos)") is ContentGenre.LECTURE
    assert parse_genre("não sei") is None and parse_genre(None) is None
    # Resposta real do Qwen3.5 para um ensaio opinativo: a palavra sem uma letra.
    assert parse_genre("opinio") is ContentGenre.OPINION
    assert parse_genre("Documento técnico") is ContentGenre.DOCUMENT


def _gen(reply="opiniao", unavailable=False):
    gen = AsyncMock()
    gen.is_available = lambda: True
    gen.last_used_reserve = False
    if unavailable:
        gen.summarize_topic.side_effect = TextGenerationUnavailableError("sem modelo")
    else:
        gen.summarize_topic.return_value = reply
    return gen


def _recording(text="Estamos diante de uma crise. " * 400):
    analysis = Analysis.new(Document.from_payload(text, []))
    analysis.chunks = [TextChunk(id="a", text=text[:100], start=0.0, end=1780.0)]
    analysis.visual_context = ["[05:32] Um homem fala ao microfone diante de uma estante."]
    return analysis


@pytest.mark.asyncio
async def test_genre_is_identified_from_samples_of_start_middle_and_end_plus_signals():
    gen = _gen("opiniao")
    analysis = _recording()

    await ContentGenreStep(gen).process(analysis)

    prompt = gen.summarize_topic.call_args.args[1]
    assert analysis.genre is ContentGenre.OPINION
    assert "gravação de cerca de 30 min" in prompt and "Um homem fala ao microfone" in prompt
    assert all(f"parte='{p}'" in prompt for p in ("início", "meio", "fim"))
    assert gen.summarize_topic.call_args.kwargs["max_tokens"] == 10


@pytest.mark.asyncio
async def test_without_a_model_or_a_valid_answer_the_genre_stays_empty():
    analysis = _recording()
    await ContentGenreStep(_gen(unavailable=True)).process(analysis)
    assert analysis.genre is None
    await ContentGenreStep(_gen("hmm")).process(analysis)
    assert analysis.genre is None


@pytest.mark.asyncio
async def test_the_summary_prompt_follows_the_genre():
    gen = _gen("# Resumo")
    analysis = _recording("Uma fala curta. " * 20)
    analysis.genre = ContentGenre.MEETING

    await SynthesisStep(gen, language="pt").process(analysis)

    prompt = gen.summarize_topic.call_args.args[1]
    assert "É uma reunião" in prompt and "as decisões tomadas" in prompt


def test_genre_is_saved_and_restored_with_the_analysis():
    analysis = _recording()
    analysis.genre = ContentGenre.LECTURE

    data = analysis_diagnostics(analysis)
    restored = Analysis.new(Document.from_payload("t", []))
    restore_from_diagnostics(restored, data)

    assert data["genre"] == "aula" and restored.genre is ContentGenre.LECTURE
    assert "genre" not in restored.diagnostics

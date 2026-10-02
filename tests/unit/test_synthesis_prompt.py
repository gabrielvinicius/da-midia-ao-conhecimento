from unittest.mock import AsyncMock

import pytest

from src.text_analysis.application.pipeline.steps import SynthesisStep
from src.text_analysis.application.ports import TextGenerationUnavailableError
from src.text_analysis.domain import Analysis, Document, TextChunk, Topic


def _analysis(text: str, chunks=None) -> Analysis:
    analysis = Analysis.new(Document.from_payload(text, []))
    analysis.chunks = chunks or []
    analysis.topics = [
        Topic(id=0, title="Topic A", keywords=["key1", "key2"], snippets=["Evidence 1", "Evidence 2"]),
        Topic(id=1, title="Topic B", keywords=["key3"], snippets=["Evidence 3"]),
    ]
    return analysis


def _text_gen(reply="# Resumo", reserve=False):
    text_gen = AsyncMock()
    text_gen.summarize_topic.return_value = reply
    text_gen.last_used_reserve = reserve
    return text_gen


@pytest.mark.asyncio
async def test_synthesis_sends_full_transcript_when_it_fits():
    text_gen = _text_gen()
    analysis = _analysis("Transcrição completa da aula sobre derivadas.")
    analysis.diagnostics["visual_context"] = ["[01:00] gráfico de uma parábola"]

    step = SynthesisStep(text_gen, language="pt", max_full_transcript_chars=1000)
    await step.process(analysis)

    prompt = text_gen.summarize_topic.call_args[0][1]
    assert prompt.startswith("<<<SYSTEM>>>")
    assert "<transcricao>" in prompt and "derivadas" in prompt
    assert "Topic A: key1, key2" in prompt
    assert "gráfico de uma parábola" in prompt
    assert "português do Brasil" in prompt
    assert analysis.diagnostics["synthesis_input"] == "full_transcript"
    assert analysis.diagnostics["summary_source"] == "llm"
    assert analysis.summary.startswith("# Resumo")


@pytest.mark.asyncio
async def test_long_recordings_are_summarized_in_sections_covering_every_chunk():
    """Antes, acima do limite, a síntese via só 5 trechos por tema; o resto da
    gravação (incluindo o que o BERTopic chamava de ruído) ficava de fora."""
    chunks = [TextChunk(id=str(i), text=f"assunto {i} " + "x" * 90, start=i * 60.0, end=i * 60.0 + 59) for i in range(30)]
    text = " ".join(c.text for c in chunks)
    replies = [f"- resumo da parte {i}" for i in range(1, 5)] + ["# Resumo final"]
    text_gen = _text_gen()
    text_gen.summarize_topic.side_effect = replies

    step = SynthesisStep(text_gen, language="pt", max_full_transcript_chars=1000, block_chars=1000)
    analysis = _analysis(text, chunks)
    await step.process(analysis)

    prompts = [call.args[1] for call in text_gen.summarize_topic.call_args_list]
    sections, final = prompts[:-1], prompts[-1]
    assert analysis.diagnostics["synthesis_input"] == "sections"
    assert analysis.diagnostics["synthesis_sections"] == len(sections) == 4
    for chunk in chunks:  # nenhum trecho da gravação fica de fora
        assert sum(chunk.text in p for p in sections) == 1
    assert "trecho 1 de 4" in sections[0] and "de 00:00 a" in sections[0]
    assert "<resumos_parciais>" in final and "resumo da parte 4" in final
    assert "<transcricao>" not in final
    assert analysis.summary.startswith("# Resumo final")


@pytest.mark.asyncio
async def test_summary_from_the_reserve_model_is_labeled_as_such():
    analysis = _analysis("Texto curto.")
    await SynthesisStep(_text_gen(reserve=True), language="pt").process(analysis)
    assert analysis.diagnostics["summary_source"] == "reserve"


@pytest.mark.asyncio
async def test_synthesis_builds_simplified_summary_when_no_model_answers():
    text_gen = _text_gen()
    text_gen.summarize_topic.side_effect = TextGenerationUnavailableError("Ollama indisponível")
    analysis = _analysis("Transcrição curta.")

    await SynthesisStep(text_gen, language="pt", max_full_transcript_chars=1000).process(analysis)

    assert analysis.diagnostics["summary_source"] == "simplified"
    assert "**Topic A** (key1, key2)" in analysis.summary
    assert "> Evidence 1" in analysis.summary  # apêndice com os trechos


@pytest.mark.asyncio
async def test_appendix_shows_when_each_excerpt_happens_and_what_was_on_screen():
    chunks = [TextChunk(id="a", text="Evidence 1", start=754.0, end=790.0)]
    analysis = _analysis("Evidence 1", chunks)
    analysis.diagnostics["visual_context"] = ["[12:40] slide with the chain rule"]

    await SynthesisStep(_text_gen(), language="pt").process(analysis)

    assert "> [12:34] Evidence 1" in analysis.summary
    assert "### O que aparecia na tela" in analysis.summary
    assert "- [12:40] slide with the chain rule" in analysis.summary


def test_summary_size_follows_the_source():
    from src.text_analysis.application.pipeline.steps import summary_target_words

    assert summary_target_words(200) == 120  # mínimo
    assert summary_target_words(3000) == 360  # ~12%
    assert summary_target_words(20000) == 900  # máximo


@pytest.mark.asyncio
async def test_short_material_gets_a_short_summary_with_a_response_cap():
    text_gen = _text_gen()
    analysis = _analysis("Uma fala curta sobre derivadas. " * 20)  # ~100 palavras

    await SynthesisStep(text_gen, language="pt").process(analysis)

    prompt = text_gen.summarize_topic.call_args.args[1]
    assert "cerca de 120 palavras" in prompt
    assert "## [Título de cada assunto principal" not in prompt  # formato curto
    assert text_gen.summarize_topic.call_args.kwargs["max_tokens"] == int(120 * 2.2) + 150
    assert analysis.diagnostics["synthesis_target_words"] == 120


@pytest.mark.asyncio
async def test_long_material_gets_sections_and_a_larger_target():
    text_gen = _text_gen()
    analysis = _analysis("Palavra " * 5000)

    await SynthesisStep(text_gen, language="pt", max_full_transcript_chars=100000).process(analysis)

    prompt = text_gen.summarize_topic.call_args.args[1]
    assert "cerca de 600 palavras" in prompt
    assert "## [Título de cada assunto principal" in prompt


@pytest.mark.asyncio
async def test_documents_are_split_without_repeating_overlapping_chunks():
    """Os trechos de documentos se sobrepõem (para a busca); juntar os trechos
    repetia ~14% do texto no resumo de documentos longos."""
    sentences = [f"Frase {i} do regimento." for i in range(60)]
    text = " ".join(sentences)
    overlapping = [TextChunk(id=str(i), text=" ".join(sentences[i:i + 3])) for i in range(0, 60, 2)]
    text_gen = _text_gen()
    text_gen.summarize_topic.side_effect = ["- parte"] * 10 + ["# Resumo"]
    analysis = _analysis(text, overlapping)

    step = SynthesisStep(text_gen, language="pt", max_full_transcript_chars=500, block_chars=500)
    await step.process(analysis)

    sections = [c.args[1] for c in text_gen.summarize_topic.call_args_list][:-1]
    joined = "".join(s.split("<trecho>\n", 1)[1] for s in sections)
    for sentence in sentences:
        assert joined.count(sentence + " ") + joined.count(sentence + "\n") == 1
    assert "de um documento" in sections[0]


@pytest.mark.asyncio
async def test_block_size_sets_how_many_items_each_part_gets():
    assert SynthesisStep.items_for("x" * 1000) == 5
    assert SynthesisStep.items_for("x" * 36000) == 14
    assert SynthesisStep.items_for("x" * 100000) == 15


@pytest.mark.asyncio
async def test_possible_truncation_is_recorded():
    text_gen = _text_gen()
    text_gen.last_prompt_tokens = 16000
    text_gen.last_prompt_truncated = True
    analysis = _analysis("Texto.")

    await SynthesisStep(text_gen, language="pt").process(analysis)

    assert analysis.diagnostics["synthesis_prompt_tokens"] == 16000
    assert analysis.diagnostics["synthesis_prompt_truncated"] is True


def test_blocks_have_similar_sizes():
    chunks = [TextChunk(id=str(i), text="y" * 999, start=i * 30.0, end=i * 30.0 + 30) for i in range(110)]
    analysis = _analysis(" ".join(c.text for c in chunks), chunks)

    blocks = SynthesisStep(_text_gen(), language="pt").split_blocks(analysis)

    sizes = [len(b["text"]) for b in blocks]
    assert len(blocks) == 4
    assert max(sizes) - min(sizes) <= 2000  # e não 36 mil + 2 mil

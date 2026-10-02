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


def _weighted_analysis(with_times=True):
    texts = ["a" * 100, "b" * 300, "c" * 100, "d" * 500]
    chunks = [
        TextChunk(id=str(i), text=t, start=(i * 600.0 if with_times else None), end=(i * 600.0 + 599 if with_times else None))
        for i, t in enumerate(texts)
    ]
    analysis = Analysis.new(Document.from_payload(" ".join(texts), []))
    analysis.chunks = chunks
    # O tema maior aparece depois: a lista precisa seguir a gravação, não o tamanho.
    analysis.topics = [
        Topic(id=0, title="Integrais", keywords=["área"], size=2, chunk_indices=[1, 3]),
        Topic(id=1, title="Derivadas", keywords=["taxa"], size=2, chunk_indices=[0, 2]),
    ]
    return analysis


def test_topics_go_in_order_of_appearance_with_share_and_start():
    from src.text_analysis.application.pipeline.steps import topic_overview

    lines, weighted = topic_overview(_weighted_analysis())

    assert weighted
    assert lines == [
        "- Derivadas (taxa): 20% do conteúdo, a partir de 00:00",
        "- Integrais (área): 80% do conteúdo, a partir de 10:00",
    ]


@pytest.mark.asyncio
async def test_prompt_asks_for_proportional_sections_with_their_start():
    text_gen = _text_gen()
    analysis = _weighted_analysis()
    analysis.document = Document.from_payload("palavra " * 3000, [])  # formato completo

    await SynthesisStep(text_gen, language="pt", max_full_transcript_chars=100000).process(analysis)

    prompt = text_gen.summarize_topic.call_args.args[1]
    assert "80% do conteúdo, a partir de 10:00" in prompt
    assert "espaço proporcional a essa parcela" in prompt
    assert "momento em que começa" in prompt


def test_documents_get_shares_but_no_times():
    from src.text_analysis.application.pipeline.steps import topic_overview

    lines, weighted = topic_overview(_weighted_analysis(with_times=False))

    assert weighted and lines[0] == "- Derivadas (taxa): 20% do conteúdo"


def test_old_topics_without_chunks_keep_the_plain_list():
    from src.text_analysis.application.pipeline.steps import topic_overview

    analysis = _analysis("Texto.")  # temas sem chunk_indices, como em análises antigas
    lines, weighted = topic_overview(analysis)

    assert not weighted
    assert lines == ["- Topic A: key1, key2", "- Topic B: key3"]


@pytest.mark.asyncio
async def test_appendix_follows_the_recording_order():
    analysis = _weighted_analysis()
    await SynthesisStep(_text_gen(), language="pt").process(analysis)

    appendix = analysis.summary.split("Apêndice", 1)[1]
    assert appendix.index("### Derivadas") < appendix.index("### Integrais")


def test_tone_is_predominant_only_with_a_clear_majority():
    from src.text_analysis.application.pipeline.steps import describe_tone
    from src.text_analysis.domain import SentimentLabel as L

    assert describe_tone([L.NEGATIVE, L.NEGATIVE, L.NEGATIVE, L.NEUTRAL]) == "negativo (3 de 4 trechos)"
    assert describe_tone([L.POSITIVE, L.NEGATIVE, L.NEUTRAL]) == "misto (3 trechos)"
    assert describe_tone([]) is None


@pytest.mark.asyncio
async def test_topics_and_the_whole_material_carry_their_tone():
    from src.text_analysis.domain import SentimentLabel as L
    from src.text_analysis.domain.entities.sentiment import Sentiment

    text_gen = _text_gen()
    analysis = _weighted_analysis()
    labels = [L.NEUTRAL, L.NEGATIVE, L.NEUTRAL, L.NEGATIVE]
    analysis.sentiments = [
        Sentiment(chunk_id=c.id, label=label, score=0.9, text=c.text) for c, label in zip(analysis.chunks, labels)
    ]

    await SynthesisStep(text_gen, language="pt").process(analysis)

    prompt = text_gen.summarize_topic.call_args.args[1]
    assert "Derivadas (taxa): 20% do conteúdo, a partir de 00:00; tom: neutro (2 de 2 trechos)" in prompt
    assert "Integrais (área): 80% do conteúdo, a partir de 10:00; tom: negativo (2 de 2 trechos)" in prompt
    assert "<tom_geral>\nmisto (4 trechos)\n</tom_geral>" in prompt
    assert "sem atribuir emoções" in prompt


@pytest.mark.asyncio
async def test_without_sentiment_the_prompt_has_no_tone():
    text_gen = _text_gen()
    await SynthesisStep(text_gen, language="pt").process(_weighted_analysis())
    prompt = text_gen.summarize_topic.call_args.args[1]
    assert "<tom_geral>" not in prompt and "; tom:" not in prompt

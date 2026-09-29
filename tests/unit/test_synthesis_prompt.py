from unittest.mock import AsyncMock

import pytest

from src.text_analysis.application.pipeline.steps import SynthesisStep
from src.text_analysis.domain import Analysis, Document, Topic


def _analysis(text: str) -> Analysis:
    analysis = Analysis.new(Document.from_payload(text, []))
    analysis.topics = [
        Topic(id=0, title="Topic A", keywords=["key1", "key2"], snippets=["Evidence 1", "Evidence 2"]),
        Topic(id=1, title="Topic B", keywords=["key3"], snippets=["Evidence 3"]),
        Topic(id=-1, title="Noise", keywords=[], snippets=["Noise 1"]),
    ]
    return analysis


@pytest.mark.asyncio
async def test_synthesis_sends_full_transcript_when_it_fits():
    text_gen = AsyncMock()
    text_gen.summarize_topic.return_value = "# Resumo"
    text_gen.last_call_used_fallback = False
    analysis = _analysis("Transcrição completa da aula sobre derivadas.")
    analysis.diagnostics["visual_context"] = ["[Visual @ 01:00]: gráfico de uma parábola"]

    step = SynthesisStep(text_gen, language="pt", max_full_transcript_chars=1000)
    await step.process(analysis)

    prompt = text_gen.summarize_topic.call_args[0][1]
    assert prompt.startswith("<<<SYSTEM>>>")
    assert "<transcricao>" in prompt and "derivadas" in prompt
    assert "Topic A: key1, key2" in prompt
    assert "gráfico de uma parábola" in prompt
    assert "português do Brasil" in prompt
    # problemas do prompt antigo não podem voltar
    assert "{max_tokens}" not in prompt and "RTX" not in prompt
    assert analysis.diagnostics["synthesis_input"] == "full_transcript"
    assert analysis.diagnostics["summary_source"] == "llm"
    assert analysis.summary.startswith("# Resumo")


@pytest.mark.asyncio
async def test_synthesis_uses_topics_when_transcript_is_too_long():
    text_gen = AsyncMock()
    text_gen.summarize_topic.return_value = "# Resumo"
    text_gen.last_call_used_fallback = True
    analysis = _analysis("x" * 500)

    step = SynthesisStep(text_gen, language="pt", max_full_transcript_chars=100)
    await step.process(analysis)

    prompt = text_gen.summarize_topic.call_args[0][1]
    assert "<transcricao>" not in prompt
    assert "<tema id='0'>" in prompt and "- Evidence 1" in prompt
    assert "<tema id='-1'>" not in prompt and "Noise 1" in prompt
    assert analysis.diagnostics["synthesis_input"] == "topics"
    assert analysis.diagnostics["summary_source"] == "fallback"

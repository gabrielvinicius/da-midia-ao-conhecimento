"""Verificação de fidelidade: frases do resumo sem apoio na transcrição."""
import numpy as np
import pytest

from src.text_analysis.application.pipeline.steps import GroundingCheckStep
from src.text_analysis.application.pipeline.synthesis import APPENDIX_MARKER
from src.text_analysis.domain import Analysis, Document, TextChunk
from src.text_analysis.domain.grounding import assess_grounding, split_sentences


def test_split_sentences_ignores_headings_markup_and_short_lines():
    md = (
        "# Aula 3 — Derivadas\n"
        "A derivada mede a taxa de variação instantânea de uma função. Ela é o limite do quociente.\n\n"
        "## Pontos-chave\n"
        "- **Regra da cadeia** deriva funções compostas de forma direta.\n"
        "- Curto demais.\n"
    )
    assert split_sentences(md) == [
        "A derivada mede a taxa de variação instantânea de uma função.",
        "Ela é o limite do quociente.",
        "Regra da cadeia deriva funções compostas de forma direta.",
    ]


def test_sentences_without_a_similar_passage_are_reported():
    passages = [[1, 0, 0], [0, 1, 0]]
    sentences = ["apoiada pelo primeiro trecho", "sem nenhum trecho parecido"]
    vectors = [[0.95, 0.31, 0], [0, 0.2, 0.98]]
    report = assess_grounding(sentences, vectors, passages, [10.0, 70.0], threshold=0.8)

    assert (report.checked, report.supported) == (2, 1)
    assert report.ratio == 0.5
    assert report.unsupported[0].text == "sem nenhum trecho parecido"
    assert report.unsupported[0].closest_start == 70.0
    assert report.to_dict()["unsupported"][0]["best_score"] < 0.8


class _Embedder:
    """Vetores por palavra-chave: frases sobre derivadas ficam perto do trecho."""

    def embed(self, texts, kind="passage"):
        out = []
        for t in texts:
            v = np.array([1.0 if "deriva" in t else 0.0, 1.0 if "futebol" in t else 0.0, 0.1])
            out.append((v / np.linalg.norm(v)).tolist())
        return out


@pytest.mark.asyncio
async def test_step_checks_only_the_summary_body_and_skips_simplified_summaries():
    analysis = Analysis.new(Document.from_payload("t"))
    analysis.chunks = [TextChunk(id="a", text="a derivada é uma taxa de variação", start=12.0)]
    analysis.chunk_embeddings = _Embedder().embed([analysis.chunks[0].text])
    analysis.summary = (
        "# Resumo\nA aula define a derivada como taxa de variação instantânea.\n"
        "O professor comenta o resultado do jogo de futebol de ontem à noite."
        + APPENDIX_MARKER + ": trechos por tema\n### Tema\n> uma frase longa do apêndice sobre futebol e outras coisas"
    )

    await GroundingCheckStep(_Embedder(), threshold=0.8).process(analysis)

    grounding = analysis.diagnostics["grounding"]
    assert grounding["checked"] == 2  # o apêndice não é verificado
    assert grounding["supported"] == 1
    assert "futebol" in grounding["unsupported"][0]["text"]

    simplified = Analysis.new(Document.from_payload("t"))
    simplified.chunks, simplified.summary = analysis.chunks, analysis.summary
    simplified.diagnostics["summary_source"] = "simplified"
    await GroundingCheckStep(_Embedder()).process(simplified)
    assert "grounding" not in simplified.diagnostics

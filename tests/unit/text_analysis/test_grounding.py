"""Verificação de fidelidade: frases do resumo sem apoio na transcrição."""
import numpy as np
import pytest

from src.text_analysis.application.pipeline.steps import GroundingCheckStep
from src.text_analysis.application.pipeline.synthesis import APPENDIX_MARKER
from src.text_analysis.domain import Analysis, Document, SummarySource, TextChunk
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

    grounding = analysis.grounding.to_dict()
    assert grounding["checked"] == 2  # o apêndice não é verificado
    assert grounding["supported"] == 1
    assert "futebol" in grounding["unsupported"][0]["text"]

    simplified = Analysis.new(Document.from_payload("t"))
    simplified.chunks, simplified.summary = analysis.chunks, analysis.summary
    simplified.summary_source = SummarySource.SIMPLIFIED
    await GroundingCheckStep(_Embedder()).process(simplified)
    assert simplified.grounding is None


def test_parts_of_the_recording_the_summary_never_mentions_are_reported():
    """Avaliação: 57 de 57 frases apoiadas num resumo sem a conclusão da aula.
    Toda frase apontava para a primeira metade; a segunda vira lacuna."""
    starts = [i * 60.0 for i in range(40)]  # 40 trechos, um por minuto
    passages = np.eye(40).tolist()
    sentences = [f"frase {i} sobre o começo da aula" for i in range(16)]
    vectors = [np.eye(40)[i].tolist() for i in range(16)]  # trechos 0 a 15

    report = assess_grounding(sentences, vectors, passages, starts, threshold=0.8)

    assert report.windows == 4  # 16 frases / 4 por janela
    assert [(round(g.start), round(g.end)) for g in report.gaps] == [(1170, 1755), (1755, 2340)]
    assert report.coverage == 0.5
    assert report.to_dict()["gaps"][0] == {"start": 1170.0, "end": 1755.0}


def test_documents_have_no_timeline_to_cover():
    report = assess_grounding(["uma frase com apoio"], [[1, 0]], [[1, 0]], [None], threshold=0.8)
    assert (report.windows, report.gaps, report.coverage) == (0, [], None)


def test_numbers_missing_from_the_passages_of_the_same_subject_are_reported():
    """O resumo trouxe "Em 1999, C# da Microsoft respondeu ao Java"; o
    apresentador situa o C# nos anos 2000."""
    passages = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    texts = ["nos anos 2000 nascia o C Sharp da Microsoft", "em 1995 nascia o Java", "uma tela com 18 camadas"]
    sentences = ["Em 1999, C# da Microsoft respondeu ao Java.", "Uma tela de login tinha 18 camadas no total."]
    vectors = [[1, 0.1, 0], [0, 0, 1]]

    report = assess_grounding(sentences, vectors, passages, [0, 60, 120], 0.8, passage_texts=texts)

    assert [(n.text, n.numbers) for n in report.number_issues] == [(sentences[0], ["1999"])]
    restored = type(report).from_dict(report.to_dict())
    assert restored.number_issues == report.number_issues and restored.gaps == report.gaps


def test_reports_saved_before_the_new_checks_still_load():
    from src.text_analysis.domain.grounding import GroundingReport

    old = GroundingReport.from_dict({"checked": 3, "supported": 3, "threshold": 0.8, "unsupported": []})
    assert (old.windows, old.gaps, old.number_issues, old.coverage) == (0, [], [], None)


def test_decades_and_sentences_with_several_facts_do_not_raise_false_alarms():
    """Na avaliação, "década de 1960" (resumo) contra "década de 60" (fala) e
    uma frase com cinco datas viravam números "a conferir"."""
    passages = np.eye(6).tolist()
    texts = ["voltamos para o fim da década de 60", "em 2001 o manifesto", "em 2003 o DDD", "em 2008 o Clean Code",
             "outra coisa", "mais outra"]
    sentences = ["O relato começa no fim da década de 1960.", "Vieram o Manifesto em 2001, o DDD em 2003 e o Clean Code em 2008."]
    vectors = [[1, 0, 0, 0, 0, 0], [0, 0.9, 0.8, 0.7, 0, 0]]

    report = assess_grounding(sentences, vectors, passages, [0, 60, 120, 180, 240, 300], 0.5, passage_texts=texts)

    assert report.number_issues == []


def test_decades_count_anywhere_in_the_recording_but_new_numbers_are_still_flagged():
    """Avaliação: "Na década de 1970..." (a fala diz "década de 70" em outro
    trecho) era falso alarme; "COVID-19" (a fala só diz "um vírus") é real."""
    passages = np.eye(8).tolist()
    texts = ["um vírus fechou tudo"] + [f"assunto {i}" for i in range(6)] + ["voltamos para a década de 70"]
    sentences = ["Na década de 1970, houve urgência técnica.", "A crise da COVID-19 fechou empresas."]
    # A frase da década aponta para trechos sem o "70" (o da década fica longe).
    vectors = [[0.1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0], [1, 0, 0, 0, 0, 0, 0, 0]]

    report = assess_grounding(sentences, vectors, passages, [i * 60.0 for i in range(8)], 0.5, passage_texts=texts)

    assert [(n.text, n.numbers) for n in report.number_issues] == [(sentences[1], ["19"])]


def test_each_number_is_checked_in_the_passage_of_its_own_context():
    """Avaliação: frases do resumo com vários fatos ("Dijkstra em 1970...
    Parnas em 1972") geravam falsos alarmes; cada número agora é conferido no
    trecho mais parecido com as palavras em volta dele."""
    from src.text_analysis.domain.grounding import number_contexts

    sentence = "Em 1970 Dijkstra criticou o GoTo, e em 1972 Parnas propôs o encapsulamento de decisões."
    assert [n for n, _ in number_contexts(sentence)] == ["1970", "1972"]
    passages = np.eye(6).tolist()
    texts = ["em 1970 Dijkstra publica o artigo", "outra", "mais outra", "nada", "nada", "em 1972 David Parnas"]
    # A frase inteira aponta para os primeiros trechos; o contexto de 1972, para o último.
    context_vectors = [[1, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1]]
    report = assess_grounding(
        [sentence], [[0.9, 0.8, 0.7, 0.1, 0.1, 0]], passages, [0, 60, 120, 180, 240, 300], 0.5,
        passage_texts=texts, context_vectors=context_vectors,
    )
    assert report.number_issues == []

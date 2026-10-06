"""Regras do perfil do conteúdo, sem modelo nem prompt."""
from src.text_analysis.domain import Sentiment, SentimentLabel as L, TextChunk, Topic
from src.text_analysis.domain.content_profile import (
    Tone,
    overall_sentiment,
    predominant_tone,
    sentiment_distribution,
    topic_profiles,
)


def test_many_neutral_chunks_outweigh_one_confident_positive():
    sentiments = [Sentiment("a", L.POSITIVE, 0.99)] + [Sentiment(str(i), L.NEUTRAL, 0.6) for i in range(5)]

    assert overall_sentiment(sentiments) == L.NEUTRAL
    assert sentiment_distribution(sentiments) == {"positive": 1, "negative": 0, "neutral": 5}
    assert overall_sentiment([]) is None


def test_tone_needs_a_clear_majority():
    assert predominant_tone([L.NEGATIVE] * 3 + [L.NEUTRAL]) == Tone(L.NEGATIVE, 3, 4)
    assert predominant_tone([L.POSITIVE, L.NEGATIVE, L.NEUTRAL]).label is None
    assert predominant_tone([]) is None


def test_topics_follow_the_recording_with_weight_start_and_tone():
    chunks = [TextChunk(str(i), "x" * size, start=i * 60.0) for i, size in enumerate((10, 30, 10, 50))]
    topics = [
        Topic(id=0, keywords=[], chunk_indices=[1, 3]),
        Topic(id=1, keywords=[], chunk_indices=[0, 2]),
        Topic(id=-1, keywords=[], chunk_indices=[]),  # sem tema: fica de fora
    ]
    sentiments = [Sentiment("1", L.NEGATIVE, 0.9), Sentiment("3", L.NEGATIVE, 0.9)]

    profiles = topic_profiles(topics, chunks, sentiments)

    assert [(p.topic.id, p.share_percent, p.start) for p in profiles] == [(1, 20, 0.0), (0, 80, 60.0)]
    assert profiles[1].tone == Tone(L.NEGATIVE, 2, 2) and profiles[0].tone is None


def test_old_topics_without_chunks_have_no_weights():
    assert topic_profiles([Topic(id=0, keywords=["a"])], [TextChunk("1", "texto")]) is None


def test_typed_fields_keep_the_stored_and_api_format():
    """Os campos tipados saem e voltam pelas mesmas chaves de ``diagnostics``
    que as análises gravadas e o frontend já usam."""
    from src.text_analysis.application.mappers import analysis_diagnostics, restore_from_diagnostics
    from src.text_analysis.domain import Analysis, Document, SummarySource
    from src.text_analysis.domain.grounding import GroundingReport

    analysis = Analysis.new(Document.from_payload("texto"))
    analysis.set_language("EN")
    analysis.visual_context = ["[00:10] slide"]
    analysis.summary_source = SummarySource.RESERVE
    analysis.grounding = GroundingReport(checked=2, supported=1, threshold=0.8)
    analysis.record_step("synthesis", 1.23456)
    analysis.record_step("sentiment", 0.5, error="sem GPU")
    analysis.diagnostics = {"indexed_chunks": 3, "_embeddings": [1]}

    data = analysis_diagnostics(analysis)
    assert data["summary_source"] == "reserve" and data["language"] == "en"
    assert data["steps"] == {"synthesis": "ok", "sentiment": "failed: sem GPU"}
    assert "_embeddings" not in data

    back = Analysis.new(Document.from_payload("texto"))
    restore_from_diagnostics(back, data)
    assert (back.summary_source, back.language, back.visual_context) == (SummarySource.RESERVE, "en", ["[00:10] slide"])
    assert back.failed_steps == ["sentiment"] and back.step_seconds["synthesis"] == 1.235
    assert back.grounding.ratio == 0.5 and back.diagnostics == {"indexed_chunks": 3}


def test_unknown_language_values_are_not_a_language():
    from src.text_analysis.domain import Analysis, Document

    analysis = Analysis.new(Document.from_payload(""))
    for value in ("auto", "unknown", "", None):
        analysis.set_language(value)
        assert analysis.language is None and analysis.language_or("pt") == "pt"


def test_storage_paths_stay_inside_the_storage_root():
    import pytest

    from src.shared.domain.errors import ValidationError
    from src.storage.domain import FilePath

    assert str(FilePath.from_path("u/2026/10/m/aula.mp4")) == "u/2026/10/m/aula.mp4"
    for bad in ("/etc/passwd", "u/../../segredo", "..", "", "..\\\\fora"):
        with pytest.raises(ValidationError):
            FilePath.from_path(bad)


def test_one_timestamp_format_for_frames_and_summaries():
    from src.shared.domain.time.timestamps import format_timestamp

    assert [format_timestamp(s) for s in (None, -3, 65, 3725)] == [None, "00:00", "01:05", "1:02:05"]

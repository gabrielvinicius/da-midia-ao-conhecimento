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

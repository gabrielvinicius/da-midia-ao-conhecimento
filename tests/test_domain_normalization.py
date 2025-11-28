import pytest

from src.text_analysis.domain import Document, EmptyTextError, SentimentLabel


def test_sentiment_label_normalization():
    assert SentimentLabel.normalize("positive") == SentimentLabel.POSITIVE
    assert SentimentLabel.normalize("NEUTRAL") == SentimentLabel.NEUTRAL
    assert SentimentLabel.normalize("neg") == SentimentLabel.NEGATIVE


def test_empty_text_error():
    with pytest.raises(EmptyTextError):
        Document.from_payload("   ")


import math

from src.media_processing.domain import Transcription
from src.media_processing.domain.transcript_confidence import transcript_confidence


def test_confidence_is_the_duration_weighted_token_probability():
    segments = [
        {"start": 0.0, "end": 30.0, "confidence": math.log(0.9)},
        {"start": 30.0, "end": 40.0, "confidence": math.log(0.5)},
    ]
    assert transcript_confidence(segments) == round((0.9 * 30 + 0.5 * 10) / 40, 3)


def test_no_segment_confidence_means_unknown_not_zero():
    assert transcript_confidence([{"start": 0, "end": 1, "text": "x"}]) is None
    assert transcript_confidence([]) is None


def test_completed_transcription_gets_its_confidence():
    """O campo ficava sempre em 0: o Whisper só dá confiança por segmento."""
    t = Transcription(media_id=__import__("uuid").uuid4())
    t.mark_as_processing()
    t.mark_as_completed({"text": "oi", "segments": [{"start": 0.0, "end": 2.0, "text": "oi", "confidence": math.log(0.8)}]})
    assert t.confidence_score == 0.8

    doc = Transcription(media_id=__import__("uuid").uuid4())
    doc.mark_as_processing()
    doc.mark_as_completed({"text": "documento", "segments": []})
    assert doc.confidence_score is None

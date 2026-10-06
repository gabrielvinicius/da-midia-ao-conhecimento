from uuid import uuid4

from src.media_processing.domain import Transcription, TranscriptionStatus


class TestTranscriptionDomain:
    def test_transcription_text_fallback(self):
        media_id = uuid4()
        # Case 1: content is set
        t1 = Transcription(media_id=media_id, text="Direct content")
        assert t1.text == "Direct content"
        t2 = Transcription(media_id=media_id, text="")
        assert t2.text == ""

    def test_mark_as_completed(self):
        media_id = uuid4()
        t = Transcription(media_id=media_id)
        t.mark_as_processing()

        result_payload = {
            "text": "Final transcription",
            "language": "pt",
            "confidence_score": 0.95,
            "segments": [{"start": 0, "end": 1, "text": "Final"}],
        }

        t.mark_as_completed(result_payload)

        assert t.status == TranscriptionStatus.COMPLETED
        assert t.text == "Final transcription"
        assert t.language == "pt"
        assert t.confidence_score == 0.95
        assert t.updated_at is not None

    def test_mark_as_failed(self):
        media_id = uuid4()
        t = Transcription(media_id=media_id)

        t.mark_as_failed("Timeout")

        assert t.status == TranscriptionStatus.FAILED
        assert t.error_message == "Timeout"
        assert t.processed_at is not None


def test_an_earlier_attempt_error_is_cleared_on_success():
    t = Transcription(media_id=uuid4())
    t.mark_as_processing()
    t.record_processing_error("sem memória na 1ª tentativa")
    t.mark_as_completed({"text": "ok"})
    assert (t.status, t.error_message) == (TranscriptionStatus.COMPLETED, None)


def test_a_finished_transcription_does_not_go_back():
    import pytest

    from src.media_processing.domain import InvalidTranscriptionTransitionError

    done = Transcription(media_id=uuid4())
    done.mark_as_processing()
    done.mark_as_completed({"text": "ok"})
    failed = Transcription(media_id=uuid4())
    failed.mark_as_failed("prazo vencido")

    for t in (done, failed):
        assert t.is_finished
        with pytest.raises(InvalidTranscriptionTransitionError):
            t.mark_as_processing()
    with pytest.raises(InvalidTranscriptionTransitionError):
        failed.mark_as_completed({"text": "tarde demais"})

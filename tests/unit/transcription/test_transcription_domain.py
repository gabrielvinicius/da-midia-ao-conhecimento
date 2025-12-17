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

        result_payload = {
            "text": "Final transcription",
            "language": "pt",
            "confidence_score": 0.95,
            "segments": [{"start": 0, "end": 1, "text": "Final"}],
            "speaker_labels": []
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

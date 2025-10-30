import pytest

from src.media_processing.transcription.infrastructure.speech_recognizer import (
    WhisperSpeechRecognizer,
)


@pytest.mark.asyncio
async def test_transcribe_returns_placeholder_payload():
    recognizer = WhisperSpeechRecognizer()

    result = await recognizer.transcribe(b"audio-bytes", language="en")

    assert result["language"] == "en"
    assert "text" in result
    assert result["provider"] == "whisper_placeholder"
    assert result["segments"]

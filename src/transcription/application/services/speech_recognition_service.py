# src/transcription/application/services/speech_recognition_service.py
from src.shared.resilience.circuit_breaker import get_circuit_breaker
from src.transcription.infrastructure.interfaces import ISpeechRecognition


class SpeechRecognitionService:
    """
    A service layer that wraps the speech recognition interface, adding resilience patterns.
    """
    def __init__(self, speech_recognition_provider: ISpeechRecognition):
        self.provider = speech_recognition_provider

    async def transcribe(self, audio_bytes: bytes, language: str) -> str:
        """
        Transcribes audio using the configured provider with a circuit breaker.
        """
        breaker_key = f"transcription_{self.provider.provider_name}"
        breaker = get_circuit_breaker(breaker_key)
        
        text = await breaker.call_async(
            self.provider.transcribe, 
            audio_bytes, 
            language=language
        )
        return text

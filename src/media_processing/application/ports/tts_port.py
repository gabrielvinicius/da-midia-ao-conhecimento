"""Porta para serviços de Text-to-Speech (Síntese de Voz)."""
from abc import ABC, abstractmethod
from typing import Optional

class TTSProviderPort(ABC):
    """Interface abstrata para geração de áudio a partir de texto."""

    @abstractmethod
    async def generate_audio(self, text: str, voice: str = "af_heart", speed: float = 1.0) -> bytes:
        """
        Gera áudio a partir do texto fornecido.
        
        Args:
            text: O texto a ser narrado.
            voice: Identificador da voz (ex: 'af_heart', 'am_adam').
            speed: Velocidade da fala.

        Returns:
            bytes: O conteúdo do arquivo de áudio (ex: WAV/MP3).
        """
        pass

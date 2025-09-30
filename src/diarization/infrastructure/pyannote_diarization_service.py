# src/diarization/infrastructure/pyannote_diarization_service.py
import torch
from pyannote.audio import Pipeline
from typing import List, Dict, Any
import structlog

from .interfaces import IDiarizationService
from ..config.settings import DiarizationSettings

logger = structlog.get_logger(__name__)

class PyannoteDiarizationService(IDiarizationService):
    """Implementation of the diarization service using pyannote.audio."""

    def __init__(self):
        try:
            settings = DiarizationSettings()
            if not settings.hf_token:
                raise ValueError("Hugging Face token (HF_TOKEN) is not set. Please get a token from https://huggingface.co/settings/tokens.")

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("diarization.service.init", device=device)

            # Initialize the pre-trained pipeline
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=settings.hf_token
            ).to(torch.device(device))

            logger.info("diarization.service.loaded", model="pyannote/speaker-diarization-3.1")

        except Exception as e:
            logger.error("diarization.service.init_failed", error=str(e))
            # Depending on the deployment strategy, you might want to handle this more gracefully
            # For now, we let it raise to prevent the application from starting in a bad state.
            raise

    def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        """Performs speaker diarization on the given audio file."""
        logger.info("diarization.process.started", audio_path=audio_path)
        try:
            diarization_result = self.pipeline(audio_path)

            segments = []
            for turn, _, speaker in diarization_result.itertracks(yield_label=True):
                segment = {
                    "speaker": speaker,
                    "start": turn.start,
                    "end": turn.end,
                }
                segments.append(segment)
            
            logger.info("diarization.process.completed", audio_path=audio_path, num_segments=len(segments))
            return segments

        except Exception as e:
            logger.error("diarization.process.failed", audio_path=audio_path, error=str(e))
            raise RuntimeError(f"Failed to diarize audio file: {audio_path}") from e

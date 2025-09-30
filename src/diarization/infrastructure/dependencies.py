# src/diarization/infrastructure/dependencies.py
from functools import lru_cache
from .interfaces import IDiarizationService
from .pyannote_diarization_service import PyannoteDiarizationService

# Use lru_cache to ensure the service is a singleton, as loading the model is expensive.
@lru_cache(maxsize=None)
def get_diarization_service() -> IDiarizationService:
    """Dependency provider for the diarization service."""
    return PyannoteDiarizationService()

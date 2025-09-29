# src/providers/api/routers.py
from typing import List
from fastapi import APIRouter

from src.storage.infrastructure.dependencies import get_available_storage_providers
from src.transcription.infrastructure.dependencies import get_available_speech_recognition_providers
from src.summarization.infrastructure.dependencies import get_available_summarizer_providers

router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)


@router.get("/storage", response_model=List[str], summary="List available storage providers")
async def list_storage_providers() -> List[str]:
    """Returns a list of available storage providers (e.g., 'local', 's3')."""
    return get_available_storage_providers()


@router.get("/transcription", response_model=List[str], summary="List available transcription providers")
async def list_transcription_providers() -> List[str]:
    """Returns a list of available speech recognition providers (e.g., 'whisper', 'fastwhisper')."""
    return get_available_speech_recognition_providers()


@router.get("/summarization", response_model=List[str], summary="List available summarization providers")
async def list_summarization_providers() -> List[str]:
    """Returns a list of available summarization providers (e.g., 'huggingface')."""
    return get_available_summarizer_providers()

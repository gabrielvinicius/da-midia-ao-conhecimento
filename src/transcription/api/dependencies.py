# src/transcription/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request

from src.transcription.bootstrap import TranscriptionContainer
from src.transcription.application.transcription_service import TranscriptionService
from src.transcription.application.commands.handlers import ProcessTranscriptionCommandHandler, SetSpeakerAliasesCommandHandler

def get_transcription_container(
    request: Request
) -> TranscriptionContainer:
    """Get the transcription dependency injection container from request."""
    return request.app.state.container["transcription_container"]

def get_transcription_service(
    container: Annotated[TranscriptionContainer, Depends(get_transcription_container)]
) -> TranscriptionService:
    """Get transcription service dependency."""
    return container.transcription_service()

def get_process_transcription_command_handler(
    container: Annotated[TranscriptionContainer, Depends(get_transcription_container)]
) -> ProcessTranscriptionCommandHandler:
    """Get process transcription command handler dependency."""
    return container.process_transcription_command_handler()

def get_set_speaker_aliases_command_handler(
    container: Annotated[TranscriptionContainer, Depends(get_transcription_container)]
) -> SetSpeakerAliasesCommandHandler:
    """Get set speaker aliases command handler dependency."""
    return container.set_speaker_aliases_command_handler()

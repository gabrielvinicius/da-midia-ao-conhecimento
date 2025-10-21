"""
Simplified transcription bootstrap using unified components
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.shared.bootstrap.unified_bootstrap import create_unified_bootstrap
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository

def bootstrap_transcription_module(db_session: AsyncSession, **kwargs) -> Dict[str, Any]:
    """Transcription bootstrap with FastWhisper integration"""
    
    bootstrap = create_unified_bootstrap(db_session)
    
    # Initialize FastWhisper integration
    from .infrastructure.fastwhisper_integration import fastwhisper_integration
    from .application.services.fastwhisper_service import fastwhisper_service
    
    base_services = bootstrap.bootstrap_media_module(
        module_name="transcription",
        repository_class=TranscriptionRepository
    )
    
    # Add FastWhisper specific services
    base_services.update({
        "fastwhisper_integration": fastwhisper_integration,
        "fastwhisper_service": fastwhisper_service,
        "primary_transcription_provider": "fastwhisper"
    })
    
    return base_services
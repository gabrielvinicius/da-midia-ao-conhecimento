# src/video_processing/application/commands/commands.py
from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID


@dataclass(frozen=True)
class ProcessVideoCommand:
    """Command to process a video."""
    media_id: str
    file_path: str
    storage_provider: str
    # Adicionar outros parâmetros necessários para o processamento de vídeo
    # Ex: generate_thumbnail: bool = True, extract_audio: bool = True, ...

# src/media_management/application/commands/create_media_command.py
from dataclasses import dataclass

@dataclass(frozen=True)
class CreateMediaCommand:
    user_id: str
    file: bytes
    filename: str
    storage_provider: str

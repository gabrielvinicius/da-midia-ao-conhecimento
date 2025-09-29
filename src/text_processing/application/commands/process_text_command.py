# src/text_processing/application/commands/process_text_command.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessTextCommand:
    media_id: str
    file_path: str
    storage_provider: str

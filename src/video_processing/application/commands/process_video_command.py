# src/video_processing/application/commands/process_video_command.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessVideoCommand:
    media_id: str
    file_path: str

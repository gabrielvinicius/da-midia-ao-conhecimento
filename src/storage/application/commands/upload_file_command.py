# src/storage/application/commands/upload_file_command.py
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UploadFileCommand:
    """Command for uploading a file (CQRS pattern)."""
    
    file_path: str
    content: bytes
    content_type: str
    user_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.file_path:
            raise ValueError("File path is required")
        if not self.content:
            raise ValueError("File content is required")
        if not self.content_type:
            raise ValueError("Content type is required")
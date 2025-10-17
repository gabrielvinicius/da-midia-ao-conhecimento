# src/storage/application/queries/get_file_query.py
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GetFileQuery:
    """Query for retrieving a file (CQRS pattern)."""
    
    file_path: str
    include_content: bool = True
    user_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.file_path:
            raise ValueError("File path is required")
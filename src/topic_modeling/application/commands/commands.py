# src/topic_modeling/application/commands/commands.py
from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID


@dataclass(frozen=True)
class AnalyzeTopicsCommand:
    """Command to analyze topics of a text."""
    media_id: str
    text_content: str
    provider: str
    language: str
    options: Optional[Dict[str, Any]] = None

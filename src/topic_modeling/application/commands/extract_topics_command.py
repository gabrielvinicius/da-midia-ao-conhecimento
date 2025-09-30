# src/topic_modeling/application/commands/extract_topics_command.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ExtractTopicsCommand:
    media_id: str
    text_content: str
    provider: str

# src/summarization/application/commands/process_summary_command.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessSummaryCommand:
    media_id: str
    text_content: str
    provider: str

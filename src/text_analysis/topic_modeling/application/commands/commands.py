"""Command objects for topic modeling workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(slots=True)
class AnalyzeTopicsCommand:
    """Command describing a topic modeling analysis request."""

    media_id: str
    text_content: str
    provider: str
    language: str
    options: Optional[Dict[str, Any]] = None
    schedule_only: bool = field(default=False)

    def should_schedule_only(self) -> bool:
        """Indicate if the command should only schedule analysis."""
        if self.schedule_only:
            return True

        if self.options:
            return bool(self.options.get("schedule_only"))

        return False

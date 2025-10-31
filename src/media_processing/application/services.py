"""Placeholder service definitions for the media processing module."""
from __future__ import annotations

from typing import Any, Optional

from src.shared.events.domain_events import MediaUploaded, TextContentReady


class MediaProcessingService:
    """Facade that will orchestrate media processing tasks in later stages."""

    async def handle_media_uploaded(
        self,
        event: MediaUploaded,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Schedule downstream processing once Stage E consolidates the module."""

        raise NotImplementedError("Stage E will provide the media processing orchestration.")

    async def handle_text_content_ready(
        self,
        event: TextContentReady,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Trigger follow-up actions after textual artefacts are generated."""

        raise NotImplementedError("Stage F will connect text analysis outputs to media workflows.")

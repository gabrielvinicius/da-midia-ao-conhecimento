# src/summarization/application/services/summary_state_service.py
from src.summarization.domain.interfaces import ISummaryRepository
from src.summarization.domain.summary import Summary


class SummaryStateService:
    """Manages the state of the Summary entity throughout the summarization process."""

    def __init__(self, summary_repository: ISummaryRepository):
        self.summary_repository = summary_repository

    async def start_processing(self, media_id: str, provider: str) -> Summary:
        """
        Finds an existing summary or creates a new one, and marks it as processing.
        """
        summary = await self.summary_repository.find_by_media_id(media_id)
        if not summary:
            summary = Summary.create(media_id=media_id, provider=provider)
        else:
            summary.provider = provider
        
        summary.process()
        await self.summary_repository.save(summary)
        return summary

    async def complete_processing(self, summary: Summary, text: str) -> Summary:
        """Marks the summary as completed and saves it."""
        summary.mark_as_completed(text)
        return await self.summary_repository.save(summary)

    async def fail_processing(self, summary: Summary, error: str) -> Summary:
        """Marks the summary as failed and saves it."""
        summary.mark_as_failed(error[:500])
        return await self.summary_repository.save(summary)

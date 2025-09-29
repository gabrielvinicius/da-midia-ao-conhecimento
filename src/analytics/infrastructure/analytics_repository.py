# src/analytics/infrastructure/analytics_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

# Import the new Media entity
from src.media_management.domain.media import Media, MediaStatus
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.summarization.domain.summary import Summary, SummaryStatus


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_average_processing_times(self) -> dict:
        """
        Calculates the average processing time for transcription and summarization
        by performing the aggregation directly in the database against the new Media entity.
        """
        stmt = (
            select(
                func.avg(
                    func.extract('epoch', Transcription.processed_at - Transcription.created_at)
                ).label("transcription_avg_seconds"),
                func.avg(
                    func.extract('epoch', Summary.processed_at - Summary.created_at)
                ).label("summarization_avg_seconds"),
                func.count(Media.id).label("total_media_analyzed")
            )
            .join(Transcription, Media.id == Transcription.media_id)
            .join(Summary, Media.id == Summary.media_id)
            .where(
                Media.status == MediaStatus.COMPLETED,
                Transcription.status == TranscriptionStatus.COMPLETED,
                Summary.status == SummaryStatus.COMPLETED
            )
        )

        result = await self.db.execute(stmt)
        row = result.first()

        if not row or row.total_media_analyzed == 0:
            return {
                "transcription_avg_seconds": 0.0,
                "summarization_avg_seconds": 0.0,
                "total_media_analyzed": 0
            }

        return {
            "transcription_avg_seconds": float(row.transcription_avg_seconds or 0.0),
            "summarization_avg_seconds": float(row.summarization_avg_seconds or 0.0),
            "total_media_analyzed": int(row.total_media_analyzed or 0)
        }

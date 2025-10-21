# src/analytics/infrastructure/analytics_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import structlog

from src.analytics.domain.interfaces import IAnalyticsRepository, ProcessingType, TimeRange
from src.media_management.domain.media import Media, MediaStatus
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.summarization.domain.summary import Summary, SummaryStatus

logger = structlog.get_logger(__name__)


class AnalyticsRepository(IAnalyticsRepository):
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
    
    async def get_processing_times_by_type(self, processing_type: ProcessingType) -> Dict[str, Any]:
        """
        Get processing times for specific operation type.
        
        Args:
            processing_type: Type of processing to analyze
            
        Returns:
            Dictionary with processing time statistics
        """
        if processing_type == ProcessingType.TRANSCRIPTION:
            stmt = (
                select(
                    func.avg(
                        func.extract('epoch', Transcription.processed_at - Transcription.created_at)
                    ).label("avg_seconds"),
                    func.min(
                        func.extract('epoch', Transcription.processed_at - Transcription.created_at)
                    ).label("min_seconds"),
                    func.max(
                        func.extract('epoch', Transcription.processed_at - Transcription.created_at)
                    ).label("max_seconds"),
                    func.count(Transcription.id).label("total_processed")
                )
                .where(Transcription.status == TranscriptionStatus.COMPLETED)
            )
        elif processing_type == ProcessingType.SUMMARIZATION:
            stmt = (
                select(
                    func.avg(
                        func.extract('epoch', Summary.processed_at - Summary.created_at)
                    ).label("avg_seconds"),
                    func.min(
                        func.extract('epoch', Summary.processed_at - Summary.created_at)
                    ).label("min_seconds"),
                    func.max(
                        func.extract('epoch', Summary.processed_at - Summary.created_at)
                    ).label("max_seconds"),
                    func.count(Summary.id).label("total_processed")
                )
                .where(Summary.status == SummaryStatus.COMPLETED)
            )
        else:
            # For other types, return empty stats
            return {
                "avg_seconds": 0.0,
                "min_seconds": 0.0,
                "max_seconds": 0.0,
                "total_processed": 0,
                "processing_type": processing_type.value
            }
        
        result = await self.db.execute(stmt)
        row = result.first()
        
        if not row or row.total_processed == 0:
            return {
                "avg_seconds": 0.0,
                "min_seconds": 0.0,
                "max_seconds": 0.0,
                "total_processed": 0,
                "processing_type": processing_type.value
            }
        
        return {
            "avg_seconds": float(row.avg_seconds or 0.0),
            "min_seconds": float(row.min_seconds or 0.0),
            "max_seconds": float(row.max_seconds or 0.0),
            "total_processed": int(row.total_processed or 0),
            "processing_type": processing_type.value
        }
    
    async def get_success_failure_rates(self, time_range: TimeRange) -> Dict[str, Any]:
        """
        Get success and failure rates for a given time range.
        
        Args:
            time_range: Time range to analyze
            
        Returns:
            Dictionary with success/failure statistics
        """
        cutoff_date = self._get_cutoff_date(time_range)
        
        # Get media statistics
        media_stmt = (
            select(
                func.count().filter(Media.status == MediaStatus.COMPLETED).label("completed"),
                func.count().filter(Media.status == MediaStatus.FAILED).label("failed"),
                func.count().label("total")
            )
            .where(Media.created_at >= cutoff_date)
        )
        
        # Get transcription statistics
        transcription_stmt = (
            select(
                func.count().filter(Transcription.status == TranscriptionStatus.COMPLETED).label("completed"),
                func.count().filter(Transcription.status == TranscriptionStatus.FAILED).label("failed"),
                func.count().label("total")
            )
            .where(Transcription.created_at >= cutoff_date)
        )
        
        # Get summarization statistics
        summary_stmt = (
            select(
                func.count().filter(Summary.status == SummaryStatus.COMPLETED).label("completed"),
                func.count().filter(Summary.status == SummaryStatus.FAILED).label("failed"),
                func.count().label("total")
            )
            .where(Summary.created_at >= cutoff_date)
        )
        
        media_result = await self.db.execute(media_stmt)
        transcription_result = await self.db.execute(transcription_stmt)
        summary_result = await self.db.execute(summary_stmt)
        
        media_row = media_result.first()
        transcription_row = transcription_result.first()
        summary_row = summary_result.first()
        
        def calculate_rate(completed: int, total: int) -> float:
            return (completed / total * 100) if total > 0 else 0.0
        
        return {
            "time_range": time_range.value,
            "cutoff_date": cutoff_date.isoformat(),
            "media": {
                "completed": media_row.completed or 0,
                "failed": media_row.failed or 0,
                "total": media_row.total or 0,
                "success_rate": calculate_rate(media_row.completed or 0, media_row.total or 0)
            },
            "transcription": {
                "completed": transcription_row.completed or 0,
                "failed": transcription_row.failed or 0,
                "total": transcription_row.total or 0,
                "success_rate": calculate_rate(transcription_row.completed or 0, transcription_row.total or 0)
            },
            "summarization": {
                "completed": summary_row.completed or 0,
                "failed": summary_row.failed or 0,
                "total": summary_row.total or 0,
                "success_rate": calculate_rate(summary_row.completed or 0, summary_row.total or 0)
            }
        }
    
    async def get_user_activity_metrics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get user activity metrics.
        
        Args:
            user_id: Optional specific user ID, if None returns all users
            
        Returns:
            Dictionary with user activity statistics
        """
        base_query = select(
            Media.user_id,
            func.count(Media.id).label("total_media"),
            func.count().filter(Media.status == MediaStatus.COMPLETED).label("completed_media"),
            func.count().filter(Media.status == MediaStatus.FAILED).label("failed_media"),
            func.count().filter(Media.status == MediaStatus.PROCESSING).label("processing_media")
        ).group_by(Media.user_id)
        
        if user_id:
            base_query = base_query.where(Media.user_id == user_id)
        
        result = await self.db.execute(base_query)
        rows = result.fetchall()
        
        if user_id:
            # Return single user metrics
            if rows:
                row = rows[0]
                return {
                    "user_id": str(row.user_id),
                    "total_media": row.total_media,
                    "completed_media": row.completed_media,
                    "failed_media": row.failed_media,
                    "processing_media": row.processing_media,
                    "success_rate": (row.completed_media / row.total_media * 100) if row.total_media > 0 else 0.0
                }
            else:
                return {
                    "user_id": str(user_id),
                    "total_media": 0,
                    "completed_media": 0,
                    "failed_media": 0,
                    "processing_media": 0,
                    "success_rate": 0.0
                }
        else:
            # Return aggregated metrics for all users
            total_users = len(rows)
            total_media = sum(row.total_media for row in rows)
            total_completed = sum(row.completed_media for row in rows)
            total_failed = sum(row.failed_media for row in rows)
            
            return {
                "total_users": total_users,
                "total_media": total_media,
                "completed_media": total_completed,
                "failed_media": total_failed,
                "overall_success_rate": (total_completed / total_media * 100) if total_media > 0 else 0.0,
                "avg_media_per_user": (total_media / total_users) if total_users > 0 else 0.0
            }
    
    async def get_media_type_distribution(self) -> Dict[str, Any]:
        """
        Get distribution of media types processed.
        
        Returns:
            Dictionary with media type distribution
        """
        stmt = (
            select(
                Media.media_type,
                func.count(Media.id).label("count"),
                func.count().filter(Media.status == MediaStatus.COMPLETED).label("completed"),
                func.count().filter(Media.status == MediaStatus.FAILED).label("failed")
            )
            .group_by(Media.media_type)
        )
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        distribution = {}
        total_media = sum(row.count for row in rows)
        
        for row in rows:
            media_type = row.media_type.value if hasattr(row.media_type, 'value') else str(row.media_type)
            distribution[media_type] = {
                "count": row.count,
                "completed": row.completed,
                "failed": row.failed,
                "percentage": (row.count / total_media * 100) if total_media > 0 else 0.0,
                "success_rate": (row.completed / row.count * 100) if row.count > 0 else 0.0
            }
        
        return {
            "total_media": total_media,
            "distribution": distribution
        }
    
    def _get_cutoff_date(self, time_range: TimeRange) -> datetime:
        """Get cutoff date based on time range."""
        now = datetime.utcnow()
        
        if time_range == TimeRange.LAST_HOUR:
            return now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_DAY:
            return now - timedelta(days=1)
        elif time_range == TimeRange.LAST_WEEK:
            return now - timedelta(weeks=1)
        elif time_range == TimeRange.LAST_MONTH:
            return now - timedelta(days=30)
        elif time_range == TimeRange.LAST_YEAR:
            return now - timedelta(days=365)
        else:
            # Default to last day
            return now - timedelta(days=1)

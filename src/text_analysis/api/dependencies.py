"""
Sentiment Analysis API dependencies - Following DDD pattern like transcription module
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.application.unified_queries import create_media_queries
from src.shared.application.unified_queries import create_user_queries

from src.shared.infrastructure.database import get_async_session


async def get_sentiment_analysis_queries(session: AsyncSession = Depends(get_async_session)):
    """Get sentiment analysis queries dependency"""
    # Using unified queries until specific sentiment analysis queries are implemented
    return create_user_queries(session)

async def get_media_queries(session: AsyncSession = Depends(get_async_session)):
    """Get media queries dependency"""
    return create_media_queries(session)
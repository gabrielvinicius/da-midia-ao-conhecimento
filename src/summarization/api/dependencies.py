"""
Summarization API dependencies - Following DDD pattern like transcription module
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.infrastructure.database import get_async_session
from src.shared.application.unified_queries import create_summary_queries
from src.shared.application.unified_queries import create_media_queries

async def get_summary_queries(session: AsyncSession = Depends(get_async_session)):
    """Get summary queries dependency"""
    return create_summary_queries(session)

async def get_media_queries(session: AsyncSession = Depends(get_async_session)):
    """Get media queries dependency"""
    return create_media_queries(session)
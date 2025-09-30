# src/summarization/infrastructure/summary_repository.py
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.summarization.domain.interfaces import ISummaryRepository
from src.summarization.domain.summary import Summary


class SummaryRepository(ISummaryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, summary: Summary) -> Summary:
        self.session.add(summary)
        await self.session.commit()
        await self.session.refresh(summary)
        return summary

    async def find_by_media_id(self, media_id: str) -> Optional[Summary]:
        """Finds a summary by its associated media ID."""
        stmt = select(Summary).where(Summary.media_id == UUID(media_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_id(self, summary_id: str) -> Optional[Summary]:
        """Finds a summary by its ID."""
        stmt = select(Summary).where(Summary.id == UUID(summary_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_media_id(self, media_id: str) -> bool:
        """Deletes a summary by its associated media ID. Returns True if deleted."""
        stmt = delete(Summary).where(Summary.media_id == UUID(media_id)).returning(Summary.id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none() is not None

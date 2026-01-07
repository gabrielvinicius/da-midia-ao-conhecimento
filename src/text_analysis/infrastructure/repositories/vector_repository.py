"""Repository for vector similarity search."""
from __future__ import annotations

from typing import List, Tuple
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.text_analysis.infrastructure.persistence.knowledge_models import KnowledgeChunkModel

class VectorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_chunks(self, media_id: UUID, chunks: List[dict]):
        """Persists multiple text chunks with their embeddings."""
        for chunk in chunks:
            record = KnowledgeChunkModel(
                media_id=media_id,
                content=chunk["text"],
                embedding=chunk["embedding"],
                metadata_json=chunk.get("metadata", {})
            )
            self.session.add(record)
        await self.session.commit()

    async def semantic_search(self, query_embedding: List[float], limit: int = 5) -> List[Tuple[KnowledgeChunkModel, float]]:
        """Performs cosine similarity search against the knowledge base."""
        # query_embedding is a list of floats
        # <-> is Euclidean distance, <=> is cosine distance
        stmt = (
            select(KnowledgeChunkModel, KnowledgeChunkModel.embedding.cosine_distance(query_embedding).label("distance"))
            .order_by(text("distance"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def delete_by_media_id(self, media_id: UUID):
        stmt = text("DELETE FROM knowledge_chunks WHERE media_id = :mid")
        await self.session.execute(stmt, {"mid": media_id})
        await self.session.commit()

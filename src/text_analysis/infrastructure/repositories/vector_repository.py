"""Repository for vector similarity search."""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.text_analysis.infrastructure.persistence.knowledge_models import (
    KnowledgeChunkModel,
)
from src.shared.infrastructure.database.unit_of_work import commit as uow_commit
from src.shared.infrastructure.database.unit_of_work import rollback as uow_rollback


class VectorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_chunks(
        self,
        media_id: UUID,
        chunks: List[dict],
        replace: bool = True,
        user_id: Optional[UUID] = None,
    ):
        """Persists multiple text chunks with their embeddings.

        Com ``replace=True`` (padrão), os trechos anteriores da mesma mídia são
        removidos na mesma transação, evitando resultados duplicados na busca
        quando uma mídia é reprocessada.
        """
        if replace:
            await self.session.execute(
                text("DELETE FROM knowledge_chunks WHERE media_id = :mid"), {"mid": media_id}
            )
        for chunk in chunks:
            record = KnowledgeChunkModel(
                media_id=media_id,
                user_id=user_id,
                content=chunk["text"],
                embedding=chunk["embedding"],
                metadata_json=chunk.get("metadata", {})
            )
            self.session.add(record)
        try:
            await uow_commit(self.session)
        except Exception:
            await uow_rollback(self.session)
            raise

    async def semantic_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        user_id: Optional[UUID] = None,
    ) -> List[Tuple[KnowledgeChunkModel, float]]:
        """Busca por similaridade de cosseno na base de conhecimento.

        Com ``user_id``, restringe a busca às mídias desse usuário.
        """
        distance = KnowledgeChunkModel.embedding.cosine_distance(query_embedding).label("distance")
        stmt = select(KnowledgeChunkModel, distance)
        if user_id is not None:
            stmt = stmt.where(KnowledgeChunkModel.user_id == user_id)
        stmt = stmt.order_by(text("distance")).limit(limit)
        result = await self.session.execute(stmt)
        return result.all()

    async def delete_by_media_id(self, media_id: UUID):
        stmt = text("DELETE FROM knowledge_chunks WHERE media_id = :mid")
        await self.session.execute(stmt, {"mid": media_id})
        await uow_commit(self.session)

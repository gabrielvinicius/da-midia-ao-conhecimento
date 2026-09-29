"""Service for Semantic Knowledge Base search."""
from __future__ import annotations

import inspect
from typing import Any, Dict, List
from uuid import UUID
import structlog

from src.text_analysis.application.ports import EmbeddingServicePort
from src.text_analysis.infrastructure.repositories.vector_repository import VectorRepository

logger = structlog.get_logger(__name__)

class KnowledgeBaseService:
    def __init__(self, vector_repo: VectorRepository, embedding_service: EmbeddingServicePort):
        self._repo = vector_repo
        self._embedding_service = embedding_service

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Performs semantic search for a given natural language query."""
        logger.info("knowledge_base.search_started", query=query)
        
        # 1. Embed the query
        embeddings = self._embedding_service.embed([query], kind="query")
        if inspect.isawaitable(embeddings):
            embeddings = await embeddings
        query_vector = embeddings[0]
        
        # 2. Search in Vector DB
        results = await self._repo.semantic_search(query_vector, limit=limit)
        
        # 3. Format results
        formatted = []
        for row, distance in results:
            formatted.append({
                "media_id": str(row.media_id),
                "content": row.content,
                "distance": float(distance),
                "relevance": round((1 - float(distance)) * 100, 1),
                "start": (row.metadata_json or {}).get("start"),
                "end": (row.metadata_json or {}).get("end"),
                "metadata": row.metadata_json
            })
            
        return formatted

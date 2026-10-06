"""SQLAlchemy models for vector-based semantic search."""
from __future__ import annotations

import uuid
from sqlalchemy import Column, ForeignKey, Text, Uuid, JSON
from pgvector.sqlalchemy import Vector
from src.shared.infrastructure.database.db import Base

class KnowledgeChunkModel(Base):
    """Stores text chunks with their associated high-dimensional embeddings."""
    __tablename__ = "knowledge_chunks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(Uuid(as_uuid=True), ForeignKey("media.id"), nullable=False, index=True)
    # Dono do trecho: a busca filtra por ele sem consultar a tabela de mídias.
    user_id = Column(Uuid(as_uuid=True), nullable=True, index=True)
    
    content = Column(Text, nullable=False)
    
    # 384 dimensões: tamanho do vetor do intfloat/multilingual-e5-small
    embedding = Column(Vector(384), nullable=False)
    
    # Metadata for time context (start/end in seconds) or speaker
    metadata_json = Column(JSON, nullable=True)

__all__ = ["KnowledgeChunkModel"]

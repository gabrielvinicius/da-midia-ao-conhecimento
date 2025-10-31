# src/topic_modeling/domain/topic_modeling.py
import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, String, DateTime, Enum as SqlEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.shared.infrastructure.database import Base
from src.topic_modeling.domain.analysis import TopicModelingStatus


class TopicModelingResult(Base):
    __tablename__ = "topic_modeling_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True)
    
    # Store the list of topics/keywords
    topics = Column(JSONB, nullable=False)
    
    # Adicionar campos de status e provedor
    status = Column(SqlEnum(TopicModelingStatus), default=TopicModelingStatus.PENDING, nullable=False)
    provider = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True) # Adicionar processed_at

    @staticmethod
    def create(media_id: UUID, provider: str) -> "TopicModelingResult":
        """Factory method to create a new topic modeling result in a valid initial state."""
        result = TopicModelingResult(media_id=media_id, provider=provider)
        result.status = TopicModelingStatus.PROCESSING
        result.created_at = datetime.utcnow()
        return result

    def mark_as_completed(self, topics_data: Dict[str, Any]):
        self.topics = topics_data
        self.status = TopicModelingStatus.COMPLETED
        self.processed_at = datetime.utcnow()
        self.error_message = None

    def mark_as_failed(self, error: str):
        self.status = TopicModelingStatus.FAILED
        self.error_message = error
        self.processed_at = datetime.utcnow()
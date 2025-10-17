# src/topic_modeling/domain/topic_modeling.py
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.shared.infrastructure.database import Base

class TopicModelingResult(Base):
    __tablename__ = "topic_modeling_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True)
    
    # Store the list of topics/keywords
    topics = Column(JSONB, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @staticmethod
    def _get_current_timestamp():
        """Get current timestamp for metadata."""
        return datetime.utcnow().isoformat()

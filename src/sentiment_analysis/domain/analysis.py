# src/sentiment_analysis/domain/analysis.py
from sqlalchemy import Column, String, Enum as SqlEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
# FIXED: Domain should not import Infrastructure - Critical DDD violation
from src.shared.domain.base_entity import BaseEntity
import enum
import uuid

class AnalysisType(str, enum.Enum):
    SENTIMENT = "SENTIMENT"
    TOPIC_MODELING = "TOPIC_MODELING" # Placeholder for future analysis

class Analysis(BaseEntity):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False)
    type = Column(SqlEnum(AnalysisType), nullable=False)
    result = Column(JSONB, nullable=False)

    __table_args__ = (UniqueConstraint('media_id', 'type', name='uq_media_id_type'),)

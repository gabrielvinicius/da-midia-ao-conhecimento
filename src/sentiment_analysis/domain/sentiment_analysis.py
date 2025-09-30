# src/sentiment_analysis/domain/sentiment_analysis.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.shared.infrastructure.database import Base

class SentimentAnalysisResult(Base):
    __tablename__ = "sentiment_analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True)
    
    # Store the overall sentiment and score
    label = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    
    # Store the full, detailed result from the provider if needed
    full_result = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

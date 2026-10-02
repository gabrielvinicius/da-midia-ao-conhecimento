"""Domain and persistence for Analysis Feedback."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, Uuid, DateTime
from src.shared.infrastructure.database.db import Base

class FeedbackModel(Base):
    """Stores user feedback on AI-generated analysis."""
    __tablename__ = "analysis_feedback"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(String, nullable=False, index=True)
    user_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    
    # 1 to 5 stars or -1/1 for thumbs
    score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    
    # Track which part of the analysis the feedback is for (summary, topics, sentiment)
    aspect = Column(String, nullable=False, default="overall")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

__all__ = ["FeedbackModel"]

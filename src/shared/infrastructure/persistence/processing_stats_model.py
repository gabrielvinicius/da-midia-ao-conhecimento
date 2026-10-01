from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from src.shared.infrastructure.database.db import Base

class ProcessingStatModel(Base):
    """
    Tabela de fatos para armazenar métricas de execução de tarefas.
    Base das estimativas e dos prazos de processamento e das medições do trabalho.
    """
    __tablename__ = "processing_stats"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String, index=True)  # ex: "video_processing", "transcription"
    
    # Métricas de Entrada
    input_size_bytes = Column(BigInteger, nullable=True)
    input_duration_seconds = Column(Float, nullable=True)
    
    # Métricas de Saída (Realidade)
    processing_duration_seconds = Column(Float, nullable=False)
    
    # Metadados
    model_name = Column(String, nullable=True) # ex: "whisper-large", "ffmpeg"
    status = Column(String, default="success")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "task_type": self.task_type,
            "input_size_bytes": self.input_size_bytes,
            "processing_duration_seconds": self.processing_duration_seconds,
            "created_at": self.created_at.isoformat()
        }

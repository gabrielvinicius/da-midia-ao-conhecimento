import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.text_analysis.application.services.text_analysis_service import TextAnalysisService
from src.text_analysis.application.ports.transcription_port import TextSourceData
from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.application.pipeline.base import AnalysisPipeline

@pytest.fixture
def mock_transcription_query_port():
    return AsyncMock()

@pytest.fixture
def mock_pipeline():
    p = MagicMock(spec=AnalysisPipeline)
    p.run = AsyncMock(side_effect=lambda x: x)
    return p

@pytest.fixture
def service(mock_transcription_query_port, mock_pipeline):
    return TextAnalysisService(
        repository=AsyncMock(),
        pipeline=mock_pipeline,
        transcription_queries=mock_transcription_query_port,
        text_analysis_read_service=AsyncMock(),
        event_bus=MagicMock(),
    )

@pytest.mark.asyncio
async def test_analyze_uses_pipeline(service, mock_transcription_query_port, mock_pipeline):
    # Arrange
    media_id = uuid4()
    command = AnalyzeTextCommand(
        media_id=media_id,
        document_id=media_id,
        text_content="Teste de pipeline",
        language="pt",
    )
    
    # Act
    await service.analyze_text_content(command)

    # Assert
    assert mock_pipeline.run.called
    service.repository.save.assert_called_once()

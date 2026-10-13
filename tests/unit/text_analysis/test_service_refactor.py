import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.text_analysis.application.services.text_analysis_service import TextAnalysisService
from src.text_analysis.application.ports.transcription_port import TextSourceData
from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.application.pipeline.base import AnalysisPipeline
from src.text_analysis.application.ports.repository import AnalysisRepositoryPort

@pytest.fixture
def mock_transcription_query_port():
    port = AsyncMock()
    port.get_text_source.return_value = TextSourceData(
        id=uuid4(), text="Teste de pipeline", language="pt", segments=[], media_id=uuid4()
    )
    port.get_media_info.return_value = {}
    return port

@pytest.fixture
def mock_pipeline():
    p = MagicMock(spec=AnalysisPipeline)
    p.run = AsyncMock(side_effect=lambda x, **_: x)
    return p

@pytest.fixture
def service(mock_transcription_query_port, mock_pipeline):
    repository = AsyncMock(spec=AnalysisRepositoryPort)
    repository.get_by_media_id.return_value = None
    repository.save_generated.side_effect = lambda analysis: str(analysis.id)
    return TextAnalysisService(
        repository=repository,
        pipeline=mock_pipeline,
        transcription_queries=mock_transcription_query_port,
        event_bus=AsyncMock(),
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
    service.repository.save_generated.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_passes_transcript_segments_to_document(service, mock_transcription_query_port, mock_pipeline):
    """O texto vem no comando, mas os segmentos (com horários) vêm da transcrição."""
    media_id = uuid4()
    segments = [{"text": "Olá", "start": 0.0, "end": 1.5}]
    mock_transcription_query_port.get_text_source.return_value = TextSourceData(
        id=uuid4(), text="Olá", language="pt", segments=segments, media_id=media_id
    )
    command = AnalyzeTextCommand(
        media_id=media_id, document_id=media_id, text_content="Olá", language="pt"
    )

    await service.analyze_text_content(command)

    analysis = mock_pipeline.run.call_args[0][0]
    assert analysis.document.segments == segments
    assert "on_step_completed" in mock_pipeline.run.call_args.kwargs


@pytest.mark.asyncio
async def test_frame_descriptions_from_processing_reach_the_summary(service, mock_transcription_query_port, mock_pipeline):
    """A análise não descreve quadros: recebe as descrições prontas com a transcrição."""
    media_id = uuid4()
    mock_transcription_query_port.get_text_source.return_value = TextSourceData(
        id=uuid4(), text="Olá", language="pt", segments=[], media_id=media_id,
        visual_context=["[00:30] um slide com um gráfico"],
    )
    command = AnalyzeTextCommand(
        media_id=media_id, document_id=media_id, text_content="Olá", language="pt"
    )

    await service.analyze_text_content(command)

    analysis = mock_pipeline.run.call_args[0][0]
    assert analysis.visual_context == ["[00:30] um slide com um gráfico"]

# src/topic_modeling/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Form
from typing import Optional, Annotated, Dict, Any

from src.shared.api.dependencies import get_current_user
from src.user_management.domain.user import User
from src.media_management.application.queries.media_queries import MediaQueries # Manter por enquanto, mas idealmente injetar via container
from src.media_processing.transcription.application.queries.transcription_queries import TranscriptionQueries # Manter por enquanto, mas idealmente injetar via container

from .dependencies import (
    get_analyze_topics_command_handler,
    get_media_queries,
    get_topic_modeling_service,
    get_transcription_queries,
)
from .schemas import TopicModelingResponse
from src.topic_modeling.application.topic_modeling_service import TopicModelingService
from src.topic_modeling.application.commands.commands import AnalyzeTopicsCommand
from src.topic_modeling.application.commands.handlers import AnalyzeTopicsCommandHandler
from src.topic_modeling.domain.topic_modeling import TopicModelingResult # Para o retorno
from src.shared.api.unified_schemas import create_success_response, create_error_response, BaseResponseSchema


router = APIRouter(prefix="/topic-modeling", tags=["Topic Modeling"])


@router.get("/", response_model=TopicModelingResponse, summary="Get topic modeling result by Media ID")
async def get_topic_modeling_result_by_media_id(
    media_id: UUID,
    topic_modeling_service: Annotated[TopicModelingService, Depends(get_topic_modeling_service)],
    current_user: User = Depends(get_current_user),
):
    """Retrieves the topic modeling result for a specific media ID."""
    # TODO: Adicionar verificação de autorização baseada no media.user_id
    # Isso exigiria injetar MediaQueries aqui ou ter um método no TopicModelingService
    # para verificar a autorização.
    
    analysis_result = await topic_modeling_service.get_topic_modeling_result(media_id)
    if not analysis_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic modeling result not found for the given media ID.")

    return analysis_result


@router.post("/analyze", response_model=BaseResponseSchema, summary="Analyze topics in text")
async def analyze_topics(
    text_content: str = Form(..., description="Text to analyze for topics"), # Renomear para text_content
    media_id: Optional[UUID] = Form(None, description="Associated media ID"), # Mudar para UUID
    provider: str = Form("bertopic_placeholder", description="Provider to use for topic modeling"), # Adicionar provider
    language: str = Form("en", description="Language of the text"), # Adicionar language
    options: Optional[Dict[str, Any]] = Form(None, description="Additional options for topic modeling"), # Adicionar options
    *,
    current_user: User = Depends(get_current_user),
    analyze_topics_handler: Annotated[AnalyzeTopicsCommandHandler, Depends(get_analyze_topics_command_handler)],
):
    """Analyze topics in provided text"""
    try:
        # Validate input
        if not text_content.strip():
            return create_error_response("Empty text provided", "Input validation failed")
        
        if len(text_content) < 100:
            return create_error_response("Text too short for topic modeling", "Input validation failed")
        
        # Criar e executar o comando AnalyzeTopicsCommand
        command = AnalyzeTopicsCommand(
            media_id=str(media_id) if media_id else str(UUID(int=0)), # Placeholder para media_id se for None
            text_content=text_content,
            provider=provider,
            language=language,
            options=options
        )
        
        result = await analyze_topics_handler.handle(command)
        
        response_data = {
            "analysis_result": result,
            "message": "Topic modeling initiated successfully"
        }
        
        return create_success_response(
            data=response_data,
            message="Topic modeling initiated"
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/reprocess", response_model=BaseResponseSchema, summary="Reprocess topic modeling")
async def reprocess_topic_modeling(
    media_id: UUID = Form(..., description="Media ID to reprocess topic modeling"),
    provider: Optional[str] = Form(None, description="Provider to use for topic modeling"),
    language: str = Form("en", description="Language of the text"),
    force: bool = Form(False, description="Force reprocessing"),
    *,
    current_user: User = Depends(get_current_user),
    analyze_topics_handler: Annotated[AnalyzeTopicsCommandHandler, Depends(get_analyze_topics_command_handler)],
    media_queries: MediaQueries = Depends(get_media_queries), # Manter por enquanto
    transcription_queries: TranscriptionQueries = Depends(get_transcription_queries), # Manter por enquanto
):
    """Reprocess topic modeling for existing media"""
    try:
        # Get media and check access
        media = await media_queries.get_by_id(str(media_id))
        
        if not media:
            return create_error_response("Media not found", "Invalid media ID")
        
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")
        
        # Check if transcription exists (required for topic modeling)
        transcription = await transcription_queries.get_by_media_id(str(media_id))
        
        if not transcription or not transcription.text:
            return create_error_response("No transcription found", "Transcription required for topic modeling")
        
        # Criar e executar o comando AnalyzeTopicsCommand
        command = AnalyzeTopicsCommand(
            media_id=str(media_id),
            text_content=transcription.text,
            provider=provider or "bertopic_placeholder",
            language=language,
            options={"force_reprocess": force}
        )
        
        result = await analyze_topics_handler.handle(command)
        
        response_data = {
            "reprocessing": {
                "media_id": str(media_id),
                "result_id": result.get("result_id"),
                "provider": provider or "bertopic_placeholder",
                "language": language,
                "status": "COMPLETED" # O handler já processa e salva o resultado
            },
            "message": "Topic modeling reprocessing started."
        }
        
        return create_success_response(
            data=response_data,
            message="Topic modeling reprocessing initiated"
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
